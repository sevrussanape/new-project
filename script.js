const API = (location.hostname === 'localhost' || location.hostname === '127.0.0.1') ? 'http://localhost:3000' : '/api';

// Every catalog item now points to a food-specific image filename.
// Existing repository food photos are used where available; legacy generic g-* / p-* assets are no longer referenced by the catalog.
const foods = [
  ['Hyderabadi Biryani', 'meals', 249, 'images/biryani.jpg', 'Aromatic basmati rice, tender chicken and house spices.'],
  ['Paneer Tikka Pizza', 'meals', 299, 'images/paneer-tikka-pizza.svg', 'Crisp crust, smoky paneer tikka and melted cheese.'],
  ['Chole Bhature', 'meals', 179, 'images/cholebhature.jpg', 'Spiced chickpeas with fluffy bhature.'],
  ['Butter Chicken', 'meals', 329, 'images/butterchicken.jpg', 'Silky tomato gravy with tender chicken.'],
  ['Masala Burger', 'snacks', 149, 'images/masala-burger.svg', 'Crispy potato patty, chutney and fresh salad.'],
  ['Vada Pav', 'snacks', 79, 'images/vada-pav.svg', 'Mumbai-style spicy potato slider with garlic chutney.'],
  ['Samosa', 'snacks', 59, 'images/samosa.svg', 'Crisp pastry filled with spiced potato and peas.'],
  ['Pani Puri', 'snacks', 69, 'images/pani-puri.svg', 'Crispy puris with tangy mint and tamarind water.'],
  ['Rasmalai Cake', 'sweets', 399, 'images/rasmalai-cake.svg', 'Soft cake layered with rasmalai cream.'],
  ['Kaju Katli', 'sweets', 249, 'images/kaju-katli.svg', 'Classic cashew fudge finished with edible silver leaf.'],
  ['Gulab Jamun', 'sweets', 129, 'images/gulab-jamun.svg', 'Warm milk dumplings soaked in saffron syrup.'],
  ['Pista Kulfi', 'sweets', 119, 'images/pista-kulfi.svg', 'Slow-churned pistachio kulfi with roasted nuts.'],
  ['Masala Chai', 'drinks', 69, 'images/masala-chai.svg', 'Aromatic Indian tea brewed with warming spices.'],
  ['Lassi', 'drinks', 99, 'images/lassi.svg', 'Cool traditional yogurt drink, lightly sweetened.'],
  ['Thandai', 'drinks', 109, 'images/thandai.svg', 'Chilled milk drink with nuts, saffron and spices.']
];

let cart = JSON.parse(localStorage.getItem('crave-cart') || '[]');
let category = 'all';
const $ = (selector) => document.querySelector(selector);

function render() {
  const query = ($('#food-search')?.value || '').trim().toLowerCase();
  const sort = $('#sort-food')?.value || 'popular';
  let list = foods.map((food, index) => ({ food, index })).filter(({ food }) =>
    (category === 'all' || food[1] === category) && food[0].toLowerCase().includes(query)
  );

  if (sort === 'low') list.sort((a, b) => a.food[2] - b.food[2]);
  if (sort === 'high') list.sort((a, b) => b.food[2] - a.food[2]);

  $('#food-grid').innerHTML = list.map(({ food, index }) => `
    <article class="food-card">
      <div class="food-img">
        <img src="${food[3]}" alt="${food[0]}" loading="lazy">
        <span class="badge">4.9 ★</span>
      </div>
      <div class="food-body">
        <div class="food-top"><h3>${food[0]}</h3><span class="price">₹${food[2]}</span></div>
        <p>${food[4]}</p>
        <div class="meta"><span>Fresh · 30–40 min</span><button class="add" data-index="${index}">Add +</button></div>
      </div>
    </article>`).join('');

  $('#empty-state').classList.toggle('hidden', !list.length);
  renderCart();
}

function renderCart() {
  const count = cart.reduce((sum, item) => sum + item.qty, 0);
  const total = cart.reduce((sum, item) => sum + item.price * item.qty, 0);
  $('#cart-count').textContent = count;
  $('#cart-total').textContent = `₹${total}`;

  $('#cart-items').innerHTML = cart.length ? cart.map((item, index) => `
    <div class="cart-line">
      <img src="${item.image}" alt="${item.name}">
      <div class="cart-line-copy"><h4>${item.name}</h4><p>₹${item.price} each</p>
        <div class="qty"><button data-action="minus" data-index="${index}">−</button><span>${item.qty}</span><button data-action="plus" data-index="${index}">+</button><button data-action="remove" data-index="${index}">Remove</button></div>
      </div>
    </div>`).join('') : '<div class="cart-empty"><p>Your bag is empty.</p><small>Add something delicious from the menu.</small></div>';

  localStorage.setItem('crave-cart', JSON.stringify(cart));
}

function toast(message) {
  const element = $('#toast');
  element.textContent = message;
  element.classList.add('show');
  setTimeout(() => element.classList.remove('show'), 2200);
}

$('#food-grid').addEventListener('click', (event) => {
  const button = event.target.closest('.add');
  if (!button) return;
  const food = foods[Number(button.dataset.index)];
  const existing = cart.find(item => item.name === food[0]);
  existing ? existing.qty++ : cart.push({ name: food[0], price: food[2], image: food[3], qty: 1 });
  renderCart();
  $('#cart-drawer').classList.add('open');
  toast(`${food[0]} added`);
});

$('#cart-items').addEventListener('click', (event) => {
  const button = event.target.closest('button');
  if (!button) return;
  const index = Number(button.dataset.index);
  if (button.dataset.action === 'plus') cart[index].qty++;
  if (button.dataset.action === 'minus') cart[index].qty--;
  if (button.dataset.action === 'remove' || cart[index]?.qty < 1) cart.splice(index, 1);
  renderCart();
});

$('#categories').addEventListener('click', (event) => {
  const button = event.target.closest('.category');
  if (!button) return;
  document.querySelectorAll('.category').forEach(item => item.classList.remove('active'));
  button.classList.add('active');
  category = button.dataset.category;
  render();
});

$('#food-search').addEventListener('input', render);
$('#sort-food').addEventListener('change', render);
$('#cart-btn').onclick = () => $('#cart-drawer').classList.add('open');
$('#close-cart').onclick = () => $('#cart-drawer').classList.remove('open');
$('#cart-overlay').onclick = () => $('#cart-drawer').classList.remove('open');
$('#search-toggle').onclick = () => { document.querySelector('#menu').scrollIntoView({ behavior: 'smooth' }); setTimeout(() => $('#food-search').focus(), 400); };
$('#scroll-how').onclick = () => $('#how').scrollIntoView({ behavior: 'smooth' });

$('#checkout-btn').onclick = () => {
  if (!cart.length) return toast('Your bag is empty');
  $('#checkout-modal').classList.remove('hidden');
};
$('#close-modal').onclick = () => $('#checkout-modal').classList.add('hidden');

$('#order-form').onsubmit = async (event) => {
  event.preventDefault();
  if (!cart.length) return toast('Your bag is empty');
  const form = new FormData(event.target);
  const items = cart.map(item => ({ name: item.name, price: item.price, image: item.image, qty: item.qty }));
  const button = event.target.querySelector('button[type="submit"]');
  button.disabled = true;
  button.innerHTML = 'Placing order…';

  try {
    const response = await fetch(`${API}/order`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ customer: { name: form.get('name'), phone: form.get('phone'), email: form.get('email'), address: form.get('address') }, items })
    });
    const data = await response.json();
    if (!response.ok || !data.success) throw new Error(data.error || 'Order failed');
    $('#form-message').textContent = `Order placed successfully · #${data.orderId}`;
    cart = [];
    renderCart();
    event.target.reset();
    toast(`Order #${data.orderId} placed`);
  } catch (error) {
    $('#form-message').textContent = 'Backend connection failed. Start the server with npm start.';
    console.error(error);
  } finally {
    button.disabled = false;
    button.innerHTML = 'Place order <i class="fa-solid fa-arrow-right"></i>';
  }
};

render();