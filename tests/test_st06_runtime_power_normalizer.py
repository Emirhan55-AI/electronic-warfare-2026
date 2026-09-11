from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def test_power_normalizer_preserves_uq28_30_wire_width(tmp_path: Path) -> None:
    compiler = shutil.which("iverilog") or "C:/msys64/ucrt64/bin/iverilog.exe"
    runtime = str(Path(compiler).with_name("vvp.exe" if compiler.lower().endswith(".exe") else "vvp"))
    tb = r'''
module tb;
reg clk=0; always #5 clk=~clk;
reg rst=0,sv=0,sl=0,mr=1; reg [3:0] nfft=12; reg [61:0] sd=0; reg [13:0] si=0;
wire sr,mv,ml,err; wire [57:0] md; wire [13:0] mi; integer count=0;
reg [57:0] expected[0:5];
axis_fft_power_normalizer dut(.aclk(clk),.aresetn(rst),.active_fft_log2(nfft),
 .s_axis_tvalid(sv),.s_axis_tready(sr),.s_axis_tdata(sd),.s_axis_tlast(sl),
 .s_axis_tuser_index(si),.m_axis_tvalid(mv),.m_axis_tready(mr),.m_axis_tdata(md),
 .m_axis_tlast(ml),.m_axis_tuser_index(mi),.status_config_error_sticky(err));
always @(posedge clk) if(rst&&mv&&mr) begin
 if(md!==expected[count] || mi!==count || ml!==(count==5)) $fatal(1,"mismatch %0d",count);
 count=count+1;
end
task sample(input [3:0] log2n,input [61:0] power,input is_last);
 begin @(negedge clk); nfft=log2n; sd=power; si=count; sl=is_last; sv=1;
  do @(posedge clk); while(!sr); @(negedge clk); sv=0; end
endtask
initial begin
 expected[0]=58'h123456789abcdef; expected[1]=58'h0; expected[2]=58'h123456789abcdef;
 expected[3]=58'h3ffffffffffffff; expected[4]=58'h123456789abcdef; expected[5]=58'h3ffffffffffffff;
 repeat(3) @(negedge clk); rst=1;
 sample(12,62'h123456789abcdef,0); sample(12,0,0);
 sample(13,62'h048d159e26af37bc,0); sample(13,62'h0fffffffffffffff,0);
 sample(14,62'h123456789abcdef0,0); sample(14,62'h3fffffffffffffff,1);
 wait(count==6); if(err) $fatal(1,"config error");
 @(negedge clk); nfft=11; @(posedge clk); @(negedge clk); if(!err) $fatal(1,"bad size not latched");
 $display("POWER_NORMALIZER_PASS"); $finish;
end
endmodule
'''
    (tmp_path / "tb.sv").write_text(tb, encoding="ascii")
    source = ROOT / "algorithms/fpga/p0/rtl/axis_fft_power_normalizer.sv"
    build = subprocess.run([compiler, "-g2012", "-s", "tb", "-o", str(tmp_path / "test.vvp"),
                            str(source), str(tmp_path / "tb.sv")], capture_output=True, text=True)
    assert build.returncode == 0, build.stderr
    run = subprocess.run([runtime, str(tmp_path / "test.vvp")], cwd=tmp_path,
                         capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "POWER_NORMALIZER_PASS" in run.stdout
