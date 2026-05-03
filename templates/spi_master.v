// SPI Master - Mode 0 (CPOL=0, CPHA=0)
// Simple 8-bit SPI master with loopback support
module spi_master #(
    parameter DATA_W = 8
)(
    input               clk,
    input               reset_n,
    input               start,
    input  [DATA_W-1:0] tx_data,
    output reg [DATA_W-1:0] rx_data,
    output reg          mosi,
    input               miso,
    output reg          sclk,
    output reg          cs_n,
    output reg          busy,
    output reg          done
);
    reg [3:0] bit_cnt;
    reg [DATA_W-1:0] shift_reg;
    reg sclk_en;
    
    always @(posedge clk) begin
        if (!reset_n) begin
            bit_cnt <= 0; shift_reg <= 0; rx_data <= 0;
            mosi <= 0; sclk <= 0; cs_n <= 1;
            busy <= 0; done <= 0; sclk_en <= 0;
        end else begin
            done <= 0;
            if (start && !busy) begin
                busy <= 1; cs_n <= 0; sclk_en <= 1;
                shift_reg <= tx_data;
                bit_cnt <= DATA_W;
            end else if (busy && bit_cnt > 0) begin
                sclk <= ~sclk;
                if (sclk) begin
                    mosi <= shift_reg[DATA_W-1];
                    shift_reg <= {shift_reg[DATA_W-2:0], miso};
                end else begin
                    bit_cnt <= bit_cnt - 1;
                    if (bit_cnt == 1) begin
                        rx_data <= {shift_reg[DATA_W-2:0], miso};
                    end
                end
            end else if (busy && bit_cnt == 0) begin
                busy <= 0; cs_n <= 1; sclk_en <= 0; done <= 1;
            end
            if (!sclk_en) sclk <= 0;
        end
    end
endmodule
