from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    data = request.json
    try:
        entry_price = float(data.get('entry_price', 0))
        grams = float(data.get('grams', 0))
        wallet_balance = float(data.get('wallet_balance', 0))
        total_charges = float(data.get('total_charges', 0))
        cmp_price = float(data.get('cmp_price', 0)) if data.get('cmp_price') else None
        
        # Sell Execution Parameters
        sell_price = float(data.get('sell_price', 0)) if data.get('sell_price') else None
        sell_grams = float(data.get('sell_grams', 0)) if data.get('sell_grams') else None
        sell_charges = float(data.get('sell_charges', 0)) if data.get('sell_charges') else 0.0

        if entry_price <= 0 or wallet_balance <= 0:
            return jsonify({'error': 'Please enter valid positive values for Entry Price and Wallet Balance.'}), 400

        # Active Position Calculations
        pos_value = entry_price * grams
        broker_margin = pos_value * 0.08  # 8% Initial Margin
        free_buffer = wallet_balance - broker_margin

        if grams > 0:
            max_loss = free_buffer + (broker_margin * 0.40)
            fall_percent = (max_loss / pos_value) * 100 if pos_value > 0 else 0
            liq_price = entry_price - (max_loss / grams)
            target_sell_price = entry_price + (max_loss / grams)
            effective_leverage = pos_value / wallet_balance if wallet_balance > 0 else 0
        else:
            max_loss = 0
            fall_percent = 0
            liq_price = 0
            target_sell_price = 0
            effective_leverage = 0

        # Sell Transaction Realization
        sell_result = None
        if sell_price and sell_grams and sell_grams > 0:
            if sell_grams > grams:
                return jsonify({'error': 'Sell quantity cannot exceed total available holdings.'}), 400
            
            gross_realized_pnl = (sell_price - entry_price) * sell_grams
            net_realized_pnl = gross_realized_pnl - sell_charges
            
            remaining_grams = grams - sell_grams
            updated_wallet_balance = wallet_balance + net_realized_pnl
            
            remaining_pos_value = entry_price * remaining_grams
            new_effective_leverage = (remaining_pos_value / updated_wallet_balance) if (updated_wallet_balance > 0 and remaining_grams > 0) else 0

            sell_result = {
                'sell_price': sell_price,
                'sell_grams': sell_grams,
                'gross_realized_pnl': gross_realized_pnl,
                'net_realized_pnl': net_realized_pnl,
                'remaining_grams': remaining_grams,
                'updated_wallet_balance': updated_wallet_balance,
                'remaining_pos_value': remaining_pos_value,
                'new_effective_leverage': new_effective_leverage
            }

        # Dynamic CMP Live Price Simulations
        cmp_sim = None
        if cmp_price and cmp_price > 0 and grams > 0:
            unrealized_pnl = (cmp_price - entry_price) * grams
            current_wallet_at_cmp = wallet_balance + unrealized_pnl
            
            # Mode 1: Pure Cash Top-up (0 grams added)
            required_wallet_m1 = (pos_value * (fall_percent / 100)) + (broker_margin * 0.60)
            pure_topup_needed = max(0, required_wallet_m1 - current_wallet_at_cmp)

            # Mode 2: Top-up + 1 Gram added
            add_grams = 1.0
            total_grams_m2 = grams + add_grams
            avg_price_m2 = ((entry_price * grams) + (cmp_price * add_grams)) / total_grams_m2
            pos_value_m2 = avg_price_m2 * total_grams_m2
            margin_m2 = pos_value_m2 * 0.08
            
            required_wallet_m2 = (pos_value_m2 * (fall_percent / 100)) + (margin_m2 * 0.60)
            add1_topup_needed = max(0, required_wallet_m2 - current_wallet_at_cmp)
            new_liq_price_m2 = avg_price_m2 * (1 - (fall_percent / 100))

            cmp_sim = {
                'cmp_price': cmp_price,
                'unrealized_pnl': unrealized_pnl,
                'pure_topup_needed': pure_topup_needed,
                'add1_topup_needed': add1_topup_needed,
                'new_avg_price': avg_price_m2,
                'new_total_grams': total_grams_m2,
                'new_liq_price': new_liq_price_m2,
                'target_fall_percent': fall_percent
            }

        return jsonify({
            'entry_price': entry_price,
            'grams': grams,
            'wallet_balance': wallet_balance,
            'pos_value': pos_value,
            'broker_margin': broker_margin,
            'free_buffer': free_buffer,
            'fall_percent': fall_percent,
            'liq_price': liq_price,
            'target_sell_price': target_sell_price,
            'effective_leverage': effective_leverage,
            'total_charges': total_charges,
            'sell_result': sell_result,
            'cmp_sim': cmp_sim
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
