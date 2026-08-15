module axis_candidate_packetizer (
  input  logic        aclk,
  input  logic        aresetn,
  input  logic        s_axis_tvalid,
  output logic        s_axis_tready,
  input  logic [57:0] s_axis_tdata,
  input  logic        s_axis_tlast,
  input  logic [11:0] s_axis_tuser_start_shifted_bin,
  input  logic [11:0] s_axis_tuser_end_shifted_bin,
  input  logic [11:0] s_axis_tuser_peak_shifted_bin,
  input  logic [11:0] s_axis_tuser_coarse_span_bins,
  input  logic [57:0] s_axis_tuser_noise,
  input  logic [61:0] s_axis_tuser_threshold,
  input  logic [1:0]  s_axis_tuser_pfa_select,
  input  logic        s_axis_tuser_evaluate_center,
  input  logic        s_axis_tuser_candidate_valid,
  output logic        m_axis_tvalid,
  input  logic        m_axis_tready,
  output logic [63:0] m_axis_tdata,
  output logic [7:0]  m_axis_tkeep,
  output logic        m_axis_tlast,
  output logic [31:0] completed_frame_count,
  output logic        status_transport_error_sticky,
  output logic        status_candidate_overflow_sticky
);
  import phase06i_pkg::*;

  typedef enum logic [2:0] {ST_INPUT, ST_HEADER, ST_RECORD, ST_DRAIN, ST_TRAILER} state_t;
  state_t state;
  logic [2:0] beat_index;
  logic [31:0] frame_id;
  logic [10:0] candidate_count;
  logic [15:0] packet_status;
  logic header_empty;
  logic stored_last;
  logic [11:0] stored_start, stored_end, stored_peak, stored_span;
  logic [57:0] stored_power, stored_noise;
  logic [61:0] stored_threshold;
  logic [1:0] stored_pfa;
  logic stored_center;
  logic [31:0] crc_state;
  logic input_shape_valid;

  function automatic logic [31:0] crc32_byte(input logic [31:0] crc_in, input logic [7:0] data);
    logic [31:0] crc;
    integer index;
    begin
      crc = crc_in ^ data;
      for (index = 0; index < 8; index = index + 1)
        crc = crc[0] ? ((crc >> 1) ^ 32'hEDB88320) : (crc >> 1);
      crc32_byte = crc;
    end
  endfunction

  function automatic logic [31:0] crc32_word(input logic [31:0] crc_in, input logic [63:0] data);
    logic [31:0] crc;
    integer index;
    begin
      crc = crc_in;
      for (index = 0; index < 8; index = index + 1)
        crc = crc32_byte(crc, data[index*8 +: 8]);
      crc32_word = crc;
    end
  endfunction

  assign input_shape_valid = s_axis_tuser_candidate_valid ?
      ((s_axis_tuser_start_shifted_bin <= s_axis_tuser_peak_shifted_bin) &&
       (s_axis_tuser_peak_shifted_bin <= s_axis_tuser_end_shifted_bin) &&
       (s_axis_tuser_coarse_span_bins ==
        (s_axis_tuser_end_shifted_bin - s_axis_tuser_start_shifted_bin + 1'b1)) &&
       (s_axis_tuser_pfa_select != 2'd3)) :
      (s_axis_tlast && s_axis_tdata == 0 && s_axis_tuser_start_shifted_bin == 0 &&
       s_axis_tuser_end_shifted_bin == 0 && s_axis_tuser_peak_shifted_bin == 0 &&
       s_axis_tuser_coarse_span_bins == 0 && s_axis_tuser_noise == 0 &&
       s_axis_tuser_threshold == 0 && s_axis_tuser_pfa_select == 0 &&
       !s_axis_tuser_evaluate_center);

  assign s_axis_tready = (state == ST_INPUT) || (state == ST_DRAIN);
  assign m_axis_tvalid = (state == ST_HEADER) || (state == ST_RECORD) || (state == ST_TRAILER);
  assign m_axis_tkeep = 8'hFF;
  assign m_axis_tlast = (state == ST_TRAILER) && (beat_index == 3);

  always_comb begin
    m_axis_tdata = 64'd0;
    case (state)
      ST_HEADER: begin
        case (beat_index)
          0: m_axis_tdata = {16'(HEADER_BYTES), 16'(ABI_VERSION), HEADER_MAGIC};
          1: m_axis_tdata = {16'(RECORD_BYTES), 16'd4096, frame_id};
          2: m_axis_tdata = {32'd0, 31'd0, header_empty};
          default: m_axis_tdata = 64'd0;
        endcase
      end
      ST_RECORD: begin
        case (beat_index)
          0: m_axis_tdata = {4'd0, stored_span, 4'd0, stored_peak,
                             4'd0, stored_end, 4'd0, stored_start};
          1: m_axis_tdata = {48'd0, 6'd0, stored_center, 1'b1, 6'd0, stored_pfa};
          2: m_axis_tdata = {6'd0, stored_power};
          3: m_axis_tdata = {6'd0, stored_noise};
          default: m_axis_tdata = {2'd0, stored_threshold};
        endcase
      end
      ST_TRAILER: begin
        case (beat_index)
          0: m_axis_tdata = {16'(TRAILER_BYTES), 16'(ABI_VERSION), TRAILER_MAGIC};
          1: m_axis_tdata = {packet_status, 5'd0, candidate_count, frame_id};
          2: m_axis_tdata = {32'(HEADER_BYTES + TRAILER_BYTES + candidate_count * RECORD_BYTES),
                             32'(candidate_count * RECORD_BYTES)};
          default: m_axis_tdata = {32'd0, crc_state ^ 32'hFFFF_FFFF};
        endcase
      end
      default: m_axis_tdata = 64'd0;
    endcase
  end

  always_ff @(posedge aclk) begin
    if (!aresetn) begin
      state <= ST_INPUT;
      beat_index <= 0;
      frame_id <= 0;
      candidate_count <= 0;
      packet_status <= 0;
      header_empty <= 0;
      stored_last <= 0;
      stored_start <= 0;
      stored_end <= 0;
      stored_peak <= 0;
      stored_span <= 0;
      stored_power <= 0;
      stored_noise <= 0;
      stored_threshold <= 0;
      stored_pfa <= 0;
      stored_center <= 0;
      crc_state <= 32'hFFFF_FFFF;
      completed_frame_count <= 0;
      status_transport_error_sticky <= 0;
      status_candidate_overflow_sticky <= 0;
    end else begin
      case (state)
        ST_INPUT: if (s_axis_tvalid && s_axis_tready) begin
          if (candidate_count == 0) begin
            header_empty <= !s_axis_tuser_candidate_valid;
            packet_status <= 0;
            crc_state <= 32'hFFFF_FFFF;
          end
          if (!input_shape_valid) begin
            packet_status[0] <= 1'b1;
            status_transport_error_sticky <= 1'b1;
            if (candidate_count == 0) header_empty <= 1'b1;
            if (s_axis_tlast) state <= ST_HEADER;
            else state <= ST_DRAIN;
            beat_index <= 0;
          end else if (!s_axis_tuser_candidate_valid) begin
            state <= ST_HEADER;
            beat_index <= 0;
          end else if (candidate_count >= MAX_CANDIDATES) begin
            packet_status[1] <= 1'b1;
            status_candidate_overflow_sticky <= 1'b1;
            if (s_axis_tlast) state <= ST_TRAILER;
            else state <= ST_DRAIN;
            beat_index <= 0;
          end else begin
            stored_last <= s_axis_tlast;
            stored_start <= s_axis_tuser_start_shifted_bin;
            stored_end <= s_axis_tuser_end_shifted_bin;
            stored_peak <= s_axis_tuser_peak_shifted_bin;
            stored_span <= s_axis_tuser_coarse_span_bins;
            stored_power <= s_axis_tdata;
            stored_noise <= s_axis_tuser_noise;
            stored_threshold <= s_axis_tuser_threshold;
            stored_pfa <= s_axis_tuser_pfa_select;
            stored_center <= s_axis_tuser_evaluate_center;
            if (candidate_count == 0) state <= ST_HEADER;
            else state <= ST_RECORD;
            beat_index <= 0;
          end
        end

        ST_HEADER: if (m_axis_tvalid && m_axis_tready) begin
          if (beat_index == 3) begin
            beat_index <= 0;
            if (header_empty) state <= ST_TRAILER;
            else state <= ST_RECORD;
          end else beat_index <= beat_index + 1'b1;
        end

        ST_RECORD: if (m_axis_tvalid && m_axis_tready) begin
          crc_state <= crc32_word(crc_state, m_axis_tdata);
          if (beat_index == 4) begin
            candidate_count <= candidate_count + 1'b1;
            beat_index <= 0;
            if (stored_last) state <= ST_TRAILER;
            else state <= ST_INPUT;
          end else beat_index <= beat_index + 1'b1;
        end

        ST_DRAIN: if (s_axis_tvalid && s_axis_tready && s_axis_tlast) begin
          if (candidate_count == 0) state <= ST_HEADER;
          else state <= ST_TRAILER;
          beat_index <= 0;
        end

        ST_TRAILER: if (m_axis_tvalid && m_axis_tready) begin
          if (beat_index == 3) begin
            state <= ST_INPUT;
            beat_index <= 0;
            frame_id <= frame_id + 1'b1;
            completed_frame_count <= completed_frame_count + 1'b1;
            candidate_count <= 0;
            header_empty <= 0;
            packet_status <= 0;
          end else beat_index <= beat_index + 1'b1;
        end
        default: state <= ST_INPUT;
      endcase
    end
  end
endmodule
