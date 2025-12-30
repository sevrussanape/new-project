const express = require('express');
const serverless = require('serverless-http');
const bodyParser = require('body-parser');
const cors = require('cors');
const fs = require('fs');
const path = require('path');

const app = express();
const router = express.Router();

app.use(cors());
app.use(bodyParser.json());

const ORDERS_FILE = path.join('/tmp', 'orders.json');

// Ensure orders file exists in /tmp
if (!fs.existsSync(ORDERS_FILE)) {
    fs.writeFileSync(ORDERS_FILE, JSON.stringify([]));
}

router.get('/orders', (req, res) => {
    try {
        const orders = JSON.parse(fs.readFileSync(ORDERS_FILE));
        res.json(orders);
    } catch (err) {
        res.json([]);
    }
});

router.post('/order', (req, res) => {
    const newOrder = req.body;
    newOrder.id = Date.now();
    newOrder.date = new Date().toLocaleString();

    try {
        const orders = JSON.parse(fs.readFileSync(ORDERS_FILE));
        orders.push(newOrder);
        fs.writeFileSync(ORDERS_FILE, JSON.stringify(orders, null, 2));
        console.log('New Order Received:', newOrder);
        res.json({ success: true, orderId: newOrder.id });
    } catch (err) {
        res.status(500).json({ success: false, error: err.message });
    }
});

app.use('/.netlify/functions/api', router);
app.use('/api', router); // Fallback

module.exports.handler = serverless(app);
