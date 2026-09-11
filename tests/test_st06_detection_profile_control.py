from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def test_profile_control_registers_and_atomic_ack(tmp_path: Path) -> None:
    compiler = shutil.which("iverilog") or "C:/msys64/ucrt64/bin/iverilog.exe"
    runtime = str(Path(compiler).with_name("vvp.exe" if compiler.lower().endswith(".exe") else "vvp"))
    tb = r'''
module tb;
reg clk=0;always #5 clk=~clk;reg rst=0,idle=1,ready=1,ap=0,rj=0;
reg [7:0] awaddr=0,araddr=0;reg awvalid=0,wvalid=0,bready=1,arvalid=0,rready=1;
reg [31:0] wdata=0;reg [3:0] wstrb=15;wire awready,wready,bvalid,arready,rvalid;
wire [1:0] bresp,rresp;wire [31:0] rdata;wire hold,cv;wire [3:0] cn;
wire [35:0] ca;wire [33:0] cw;reg [3:0] an=12;reg [35:0] aa=36'd36851433755;
reg [33:0] aw=34'd17098572778;
p0_detection_profile_control dut(.aclk(clk),.aresetn(rst),.s_axi_awaddr(awaddr),
 .s_axi_awvalid(awvalid),.s_axi_awready(awready),.s_axi_wdata(wdata),.s_axi_wstrb(wstrb),
 .s_axi_wvalid(wvalid),.s_axi_wready(wready),.s_axi_bresp(bresp),.s_axi_bvalid(bvalid),
 .s_axi_bready(bready),.s_axi_araddr(araddr),.s_axi_arvalid(arvalid),.s_axi_arready(arready),
 .s_axi_rdata(rdata),.s_axi_rresp(rresp),.s_axi_rvalid(rvalid),.s_axi_rready(rready),
 .pipeline_idle(idle),.hold_input(hold),.config_valid(cv),.config_ready(ready),
 .config_fft_log2(cn),.config_alpha_q32(ca),.config_weak_alpha_q32(cw),
 .config_applied(ap),.config_rejected(rj),.active_fft_log2(an),
 .active_alpha_q32(aa),.active_weak_alpha_q32(aw));
task write(input[7:0]a,input[31:0]d,input[1:0]response);
 begin @(negedge clk);awaddr=a;wdata=d;awvalid=1;wvalid=1;@(negedge clk);awvalid=0;wvalid=0;
  wait(bvalid);if(bresp!==response)$fatal(1,"write response %h",a);@(negedge clk);end
endtask
task read(input[7:0]a,input[31:0]expected);
 begin @(negedge clk);araddr=a;arvalid=1;@(negedge clk);arvalid=0;wait(rvalid);
  if(rresp!=0||rdata!==expected)$fatal(1,"read %h got=%h",a,rdata);@(negedge clk);end
endtask
initial begin
 repeat(3)@(negedge clk);rst=1;
 read(0,32'h53540602);read('h0c,12);read('h34,12);
 write('h0c,11,2);read('h0c,12);write('h0c,14,0);read('h0c,14);
 write('h10,32'h0,0);write('h14,2,0);write('h18,32'h0,0);write('h1c,1,0);
 fork begin write('h08,1,0);end begin wait(cv);if(cn!=14||ca!=36'h200000000||cw!=34'h100000000||!hold)$fatal(1,"profile launch");
  @(negedge clk);an=14;aa=ca;aw=cw;ap=1;@(negedge clk);ap=0;end join
 read('h30,1);read('h34,14);read('h20,32'h0);read('h24,2);
 $display("PROFILE_CONTROL_PASS");$finish;
end
endmodule
'''
    (tmp_path / "tb.sv").write_text(tb, encoding="ascii")
    sources = [ROOT / "algorithms/fpga/p0/rtl/p0_os_cfar_pkg.sv",
               ROOT / "algorithms/fpga/p0/rtl/p0_detection_profile_control.sv",
               tmp_path / "tb.sv"]
    build = subprocess.run([compiler,"-g2012","-s","tb","-o",str(tmp_path/"test.vvp"),
                            *(str(path) for path in sources)],capture_output=True,text=True)
    assert build.returncode == 0, build.stderr
    run = subprocess.run([runtime,str(tmp_path/"test.vvp")],cwd=tmp_path,capture_output=True,text=True,timeout=30)
    assert run.returncode == 0, run.stdout+run.stderr
    assert "PROFILE_CONTROL_PASS" in run.stdout
