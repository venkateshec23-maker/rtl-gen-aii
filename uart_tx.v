`timescale 1ns/1ps

module uart_tx (
    input clk,
    input reset_n,
    input tx_start,
    input [7:0] data_in,
    input [15:0] baud_div,
    output reg tx_out,
    output reg tx_busy,
    output reg tx_done
);

    localparam IDLE = 2'b00;
    localparam TX   = 2'b01;
    localparam STOP = 2'b10;

    reg [1:0] state;
    reg [15:0] baud_cnt;
    reg [3:0] bit_idx;
    reg [7:0] tx_data;
    reg tx_start_d;

    always @(posedge clk) begin
        if (!reset_n) begin
            state <= IDLE;
            tx_out <= 1;
            tx_busy <= 0;
            tx_done <= 0;
            baud_cnt <= 0;
            bit_idx <= 0;
            tx_data <= 0;
            tx_start_d <= 0;
        end else begin
            tx_start_d <= tx_start;
            tx_done <= 0;

            case (state)
                IDLE: begin
                    tx_out <= 1;
                    tx_busy <= 0;
                    baud_cnt <= 0;
                    bit_idx <= 0;
                    if (tx_start && !tx_start_d && !tx_busy) begin
                        tx_data <= data_in;
                        tx_busy <= 1;
                        state <= TX;
                        baud_cnt <= baud_div - 1;
                        tx_out <= 0;
                        bit_idx <= 1;
                    end
                end

                TX: begin
                    if (baud_cnt == 0) begin
                        baud_cnt <= baud_div - 1;
                        if (bit_idx < 8) begin
                            tx_out <= tx_data[bit_idx - 1];
                            bit_idx <= bit_idx + 1;
                        end else if (bit_idx == 8) begin
                            tx_out <= 1;
                            bit_idx <= 9;
                        end else if (bit_idx == 9) begin
                            tx_done <= 1;
                            state <= IDLE;
                            bit_idx <= 0;
                        end
                    end else begin
                        baud_cnt <= baud_cnt - 1;
                    end
                end

                default: begin
                    state <= IDLE;
                    tx_out <= 1;
                    tx_busy <= 0;
                end
            endcase
        end
    end

endmodule