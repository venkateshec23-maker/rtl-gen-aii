`timescale 1ns/1ps

module spi_master_fifo (
    input clk,
    input reset_n,
    input [7:0] data_in,
    input tx_start,
    input miso,
    output reg [7:0] data_out,
    output reg tx_done,
    output reg sclk,
    output reg mosi,
    output reg cs_n
);

    localparam IDLE = 3'd0;
    localparam TRANSFER = 3'd1;
    localparam DONE = 3'd2;

    reg [2:0] state;
    reg [2:0] next_state;
    reg [7:0] shift_reg;
    reg [2:0] bit_count;
    reg [1:0] sclk_div;
    reg miso_sync;

    always @(*) begin
        next_state = state;
        case (state)
            IDLE: begin
                if (tx_start) begin
                    next_state = TRANSFER;
                end
            end
            TRANSFER: begin
                if (bit_count == 7 && sclk_div == 2) begin
                    next_state = DONE;
                end
            end
            DONE: begin
                next_state = IDLE;
            end
            default: next_state = IDLE;
        endcase
    end

    always @(posedge clk) begin
        if (!reset_n) begin
            state <= IDLE;
            data_out <= 0;
            tx_done <= 0;
            sclk <= 0;
            mosi <= 0;
            cs_n <= 1;
            shift_reg <= 0;
            bit_count <= 0;
            sclk_div <= 0;
            miso_sync <= 0;
        end else begin
            miso_sync <= miso;
            state <= next_state;

            case (state)
                IDLE: begin
                    tx_done <= 0;
                    cs_n <= 1;
                    sclk <= 0;
                    bit_count <= 0;
                    sclk_div <= 0;
                    if (tx_start) begin
                        shift_reg <= data_in;
                        cs_n <= 0;
                        mosi <= data_in[7];
                    end
                end

                TRANSFER: begin
                    cs_n <= 0;

                    if (sclk_div == 2) begin
                        sclk_div <= 0;
                        if (bit_count < 7) begin
                            bit_count <= bit_count + 1;
                            shift_reg <= {shift_reg[6:0], miso_sync};
                            mosi <= shift_reg[6];
                        end else begin
                            shift_reg <= {shift_reg[6:0], miso_sync};
                        end
                    end else begin
                        sclk_div <= sclk_div + 1;
                    end

                    if (sclk_div == 0 || sclk_div == 1) begin
                        sclk <= 1;
                    end else begin
                        sclk <= 0;
                    end
                end

                DONE: begin
                    data_out <= shift_reg;
                    tx_done <= 1;
                    cs_n <= 1;
                    sclk <= 0;
                    mosi <= 0;
                end
            endcase
        end
    end

endmodule