def format_payment(order):
    return f"💳 Payment Order Created\nID: {order['id']}\nAmount: ₹{order['amount']/100}"
