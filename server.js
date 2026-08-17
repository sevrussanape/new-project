const express = require('express');
const cors = require('cors');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());
app.use(express.static(__dirname));

const orders = [];

app.get('/', (req, res) => res.sendFile(__dirname + '/index.html'));
app.get('/admin', (req, res) => res.sendFile(__dirname + '/admin.html'));
app.get('/health', (req, res) => res.json({ status: 'ok', service: 'crave-api' }));
app.get('/orders', (req, res) => res.json(orders));

app.post('/order', (req, res) => {
  const { customer, items } = req.body || {};
  if (!customer?.name || !customer?.email || !customer?.phone || !customer?.address) {
    return res.status(400).json({ success: false, error: 'Complete customer details are required.' });
  }
  if (!Array.isArray(items) || items.length === 0) {
    return res.status(400).json({ success: false, error: 'At least one item is required.' });
  }
  const safeItems = items.map(item => ({ name: String(item.name || 'Item'), price: Number(item.price) || 0, qty: Math.max(1, Number(item.qty) || 1) }));
  const calculatedTotal = safeItems.reduce((sum, item) => sum + item.price * item.qty, 0);
  const order = { id: `CRV-${Date.now()}`, date: new Date().toISOString(), status: 'Pending', customer, items: safeItems, total: Number(calculatedTotal.toFixed(2)) };
  orders.unshift(order);
  res.status(201).json({ success: true, orderId: order.id, order });
});

app.patch('/orders/:id/status', (req, res) => {
  const order = orders.find(item => item.id === req.params.id);
  const allowed = ['Pending', 'Preparing', 'Out for delivery', 'Delivered', 'Cancelled'];
  if (!order) return res.status(404).json({ success: false, error: 'Order not found.' });
  if (!allowed.includes(req.body?.status)) return res.status(400).json({ success: false, error: 'Invalid order status.' });
  order.status = req.body.status;
  res.json({ success: true, order });
});

app.listen(PORT, () => console.log(`Crave server running on http://localhost:${PORT}`));
