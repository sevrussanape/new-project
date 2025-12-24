const express = require('express');
const fs = require('fs');
const cors = require('cors');
const bodyParser = require('body-parser');

const app = express();
const PORT = 3000;

app.use(cors());
app.use(bodyParser.json());

const ORDERS_FILE = 'orders.json';

// Ensure orders file exists
if (!fs.existsSync(ORDERS_FILE)) {
    fs.writeFileSync(ORDERS_FILE, JSON.stringify([]));
}

// Get all orders (for Admin)
app.get('/orders', (req, res) => {
    const orders = JSON.parse(fs.readFileSync(ORDERS_FILE));
    res.json(orders);
});

// Place a new order
app.post('/order', (req, res) => {
    const newOrder = req.body;
    newOrder.id = Date.now();
    newOrder.date = new Date().toLocaleString();

    const orders = JSON.parse(fs.readFileSync(ORDERS_FILE));
    orders.push(newOrder);

    fs.writeFileSync(ORDERS_FILE, JSON.stringify(orders, null, 2));

    console.log('New Order Received:', newOrder);
    res.json({ success: true, orderId: newOrder.id });
});

app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
});
