"""AXI-Lite configuration transaction and readback checks."""
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_control_transactions(tmp_path):
    tb = r'''
module tb;
 reg clk=0; always #5 clk=~clk;
 reg rst=0;
 reg [7:0] awaddr=0, araddr=0;
 reg awvalid=0,wvalid=0,bready=0,arvalid=0,rready=0;
 reg [31:0] wdata=0; reg [3:0] wstrb=15;
 wire awready,wready,bvalid,arready,rvalid;
 wire [1:0] bresp,rresp; wire [31:0] rdata;
 reg idle=1, cr=1, ap=0,rj=0;
 wire hold_input,cv; wire [35:0] ca; wire [33:0] cw;
 reg [35:0] aa=36'd36851433755; reg [33:0] wa=34'd17098572778;
 reg reject_next=0;
 integer commits=0, cycles=0;
 p0_detection_control dut(
 .aclk(clk),.aresetn(rst),.s_axi_awaddr(awaddr),.s_axi_awvalid(awvalid),.s_axi_awready(awready),
 .s_axi_wdata(wdata),.s_axi_wstrb(wstrb),.s_axi_wvalid(wvalid),.s_axi_wready(wready),
 .s_axi_bresp(bresp),.s_axi_bvalid(bvalid),.s_axi_bready(bready),
 .s_axi_araddr(araddr),.s_axi_arvalid(arvalid),.s_axi_arready(arready),
 .s_axi_rdata(rdata),.s_axi_rresp(rresp),.s_axi_rvalid(rvalid),.s_axi_rready(rready),
 .pipeline_idle(idle),.hold_input(hold_input),.config_valid(cv),.config_ready(cr),
 .config_alpha_q32(ca),.config_weak_alpha_q32(cw),.config_applied(ap),.config_rejected(rj),
 .active_alpha_q32(aa),.active_weak_alpha_q32(wa));
 always @(posedge clk) begin
  cycles=cycles+1; if(cycles>2000) $fatal(1,"timeout");
  ap<=0; rj<=0;
  if(rst && cv && cr) begin
   if(!hold_input) $fatal(1,"input not held during commit");
   commits=commits+1;
   if(reject_next) rj<=1;
   else begin aa<=ca; wa<=cw; ap<=1; end
  end
 end
 task address(input [7:0] a);
  begin
   @(negedge clk); awaddr=a; awvalid=1;
   do @(posedge clk); while(!awready);
   @(negedge clk); awvalid=0;
  end
 endtask
 task data(input [31:0] d,input [3:0] st);
  begin
   @(negedge clk); wdata=d; wstrb=st; wvalid=1;
   do @(posedge clk); while(!wready);
   @(negedge clk); wvalid=0;
  end
 endtask
 task response(input [1:0] expected);
  begin
   wait(bvalid); @(negedge clk);
   repeat(3) begin
    if(!bvalid || bresp!==expected || awready || wready) $fatal(1,"write response/backpressure");
    @(negedge clk);
   end
   bready=1; @(negedge clk); bready=0;
  end
 endtask
 task write_reg(input [7:0] a,input [31:0] d,input integer order,input [3:0] st,input [1:0] result);
  begin
   if(order==0) begin address(a); repeat(2) @(negedge clk); data(d,st); end
   else if(order==1) begin data(d,st); repeat(2) @(negedge clk); address(a); end
   else fork address(a); data(d,st); join
   response(result);
  end
 endtask
 task read_reg(input [7:0] a,input [31:0] d,input [1:0] result);
  begin
   @(negedge clk); araddr=a; arvalid=1;
   do @(posedge clk); while(!arready);
   @(negedge clk); arvalid=0;
   wait(rvalid);
   repeat(3) begin
    if(!rvalid || rdata!==d || rresp!==result || arready) $fatal(1,"read %h got %h expected %h",a,rdata,d);
    @(negedge clk);
   end
   rready=1; @(negedge clk); rready=0;
  end
 endtask
 initial begin
  repeat(3) @(negedge clk); rst=1;
  read_reg(0,32'h53540601,0);
  read_reg(8'h30,0,0);
  write_reg(8'h10,0,0,15,0);
  write_reg(8'h14,2,1,15,0);
  write_reg(8'h18,0,2,15,0);
  write_reg(8'h1c,1,0,15,0);
  read_reg(8'h24,8,0); // draft is not active
  write_reg(8'h08,1,2,15,0);
  read_reg(8'h24,2,0); read_reg(8'h2c,1,0); read_reg(8'h30,1,0);
  idle=0; write_reg(8'h08,1,0,15,2); idle=1;
  cr=0; write_reg(8'h08,1,1,15,2); cr=1;
  write_reg(8'h14,16,0,15,2); // reject high-bit truncation
  write_reg(8'h1c,4,0,15,2);
  write_reg(8'h14,0,1,1,2); // no partial word writes
  write_reg(8'h15,0,2,15,2);
  write_reg(8'h00,0,0,15,2); // read only
  write_reg(8'h08,0,1,15,2);
  read_reg(8'hff,0,2);
  write_reg(8'h1c,3,0,15,0); // weak above normal
  write_reg(8'h08,1,0,15,2);
  read_reg(8'h30,1,0);
  write_reg(8'h1c,1,0,15,0);
  reject_next=1;
  write_reg(8'h08,1,2,15,2);
  read_reg(8'h30,1,0);
  if(commits!=2 || hold_input || cv) $fatal(1,"commit lifecycle");
  // Reset with an unmatched AW must discard that request.
  address(8'h08); @(negedge clk); rst=0;
  repeat(2) @(negedge clk); rst=1;
  read_reg(8'h30,0,0); read_reg(8'h14,8,0);
  if(bvalid || hold_input || cv) $fatal(1,"reset incomplete");
  $display("DETECTION_CONTROL_PASS"); $finish;
 end
endmodule
'''
    (tmp_path / 'tb.sv').write_text(tb)
    compiler = shutil.which('iverilog') or 'C:/msys64/ucrt64/bin/iverilog.exe'
    runtime = str(Path(compiler).with_name('vvp.exe' if compiler.lower().endswith('.exe') else 'vvp'))
    rtl = ROOT / 'algorithms/fpga/p0/rtl'
    built = subprocess.run([compiler, '-g2012', '-s', 'tb', '-o', str(tmp_path/'test.vvp'),
                           str(rtl/'p0_os_cfar_pkg.sv'), str(rtl/'p0_detection_control.sv'),
                           str(tmp_path/'tb.sv')], capture_output=True, text=True)
    assert built.returncode == 0, built.stderr
    run = subprocess.run([runtime, str(tmp_path/'test.vvp')], capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stdout + run.stderr
    assert 'DETECTION_CONTROL_PASS' in run.stdout
