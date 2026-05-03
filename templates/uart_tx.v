// UART Transmitter - 8N1 format
// Simple UART TX with programmable baud rate
module uart_tx #(
    parameter BAUD_DIV = 10416
)(
    input            clk,
    input            reset_n,
    input      [7:0] tx_data,
    input            tx_start,
    output reg       tx,
    output reg       tx_busy
);
    localparam IDLE=2'd0, START=2'd1, DATA=2'd2, STOP=2'd3;
    reg [1:0]  state;
    reg [13:0] baud_cnt;
    reg [2:0]  bit_idx;
    reg [7:0]  shift_reg;
    
    always @(posedge clk) begin
        if (!reset_n) begin
            state<=IDLE; tx<=1'b1; tx_busy<=0;
            baud_cnt<=0; bit_idx<=0; shift_reg<=0;
        end else begin
            case (state)
                IDLE: begin
                    tx<=1'b1; tx_busy<=0;
                    if (tx_start) begin
                        shift_reg<=tx_data; baud_cnt<=0;
                        bit_idx<=0; tx_busy<=1'b1;
                        state<=START;
                    end
                end
                START: begin
                    tx<=1'b0;
                    if (baud_cnt==BAUD_DIV-1) begin
                        baud_cnt<=0; state<=DATA;
                    end else baud_cnt<=baud_cnt+1;
                end
                DATA: begin
                    tx<=shift_reg[0];
                    if (baud_cnt==BAUD_DIV-1) begin
                        baud_cnt<=0;
                        shift_reg<={1'b0,shift_reg[7:1]};
                        if (bit_idx==7) begin
                            bit_idx<=0; state<=STOP;
                        end else bit_idx<=bit_idx+1;
                    end else baud_cnt<=baud_cnt+1;
                end
                STOP: begin
                    tx<=1'b1;
                    if (baud_cnt==BAUD_DIV-1) begin
                        baud_cnt<=0; state<=IDLE;
                    end else baud_cnt<=baud_cnt+1;
                end
                default: state<=IDLE;
            endcase
        end
    end
endmodule
