let menu = document.querySelector('#menu-bar');
let navbar = document.querySelector('.navbar');

menu.onclick = () => {
  menu.classList.toggle('fa-times');
  navbar.classList.toggle('active');
}

let cartBtn = document.querySelector('#cart-btn');
let closeCartBtn = document.querySelector('#close-cart-btn');
let shoppingCartContainer = document.querySelector('.shopping-cart-container');

cartBtn.onclick = () => {
  shoppingCartContainer.classList.add('active');
}

closeCartBtn.onclick = () => {
  shoppingCartContainer.classList.remove('active');
}

window.onscroll = () => {
  menu.classList.remove('fa-times');
  navbar.classList.remove('active');
  shoppingCartContainer.classList.remove('active');

  if (window.scrollY > 60) {
    document.querySelector('#scroll-top').classList.add('active');
  } else {
    document.querySelector('#scroll-top').classList.remove('active');
  }
}

function loader() {
  document.querySelector('.loader-container').classList.add('fade-out');
}

function fadeOut() {
  setInterval(loader, 3000);
}

window.onload = fadeOut();


// Shopping Cart Logic
let cart = JSON.parse(localStorage.getItem('food-cart')) || [];

function updateCartUI() {
  let cartContainer = document.querySelector('.cart-items-container');
  let totalSpan = document.querySelector('.cart-total span');

  // clear current items
  cartContainer.innerHTML = '';

  if (cart.length === 0) {
    cartContainer.innerHTML = '<p class="empty-cart-msg">Your cart is empty</p>';
    totalSpan.innerText = '$0.00';
    return;
  }

  let total = 0;

  cart.forEach((item, index) => {
    total += item.price * item.qty;
    let cartItem = document.createElement('div');
    cartItem.classList.add('cart-item');
    cartItem.innerHTML = `
            <div class="fas fa-times" onclick="removeFromCart(${index})"></div>
            <img src="${item.image}" alt="">
            <div class="content">
                <h3>${item.name}</h3>
                <span class="qty">${item.qty} x </span>
                <span class="price">₹${item.price}</span>
            </div>
        `;
    cartContainer.appendChild(cartItem);
  });

  totalSpan.innerText = '₹' + total.toFixed(2);
  localStorage.setItem('food-cart', JSON.stringify(cart));
}

function addToCart(name, price, image) {
  // check if item already exists
  let existingItem = cart.find(item => item.name === name);
  if (existingItem) {
    existingItem.qty++;
  } else {
    cart.push({ name, price, image, qty: 1 });
  }
  updateCartUI();
  shoppingCartContainer.classList.add('active'); // open cart
}

function removeFromCart(index) {
  cart.splice(index, 1);
  updateCartUI();
}

// Attach listeners to "Order Now" buttons in Popular section (where prices exist)
document.addEventListener('DOMContentLoaded', () => {
  // Select buttons in "popular" section
  let buttons = document.querySelectorAll('.popular .box .btn');

  buttons.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      let box = btn.parentElement;
      let name = box.querySelector('h3').innerText;
      let image = box.querySelector('img').src;
      let priceText = box.querySelector('.price').innerText;
      // format likely "$5 - $20", we'll just take the first number for simplicity
      // or we can generate a random price between the range. let's just parse $5.
      let price = parseFloat(priceText.replace(/[^0-9.-]+/g, ""));
      if (isNaN(price)) price = 10; // default fallout

      addToCart(name, price, image);
    });
  });

  // Handle styling for other sections if needed or add fallback listeners
  // For gallery or home where there is no price, we can add default pricing
  let otherButtons = document.querySelectorAll('.gallery .box .btn, .home .content .btn');
  otherButtons.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      // For home, getting image is different
      let parent = btn.parentElement;
      let container = parent.parentElement; // .home

      let name = "Delicious Food";
      let image = "images/home-img.png";
      let price = 15; // default

      if (parent.classList.contains('content') && container.classList.contains('box')) {
        // Gallery
        name = parent.querySelector('h3').innerText;
        // Image is sibling of content in gallery structure?
        // .gallery .box img is sibling of .content
        let imgEl = container.querySelector('img');
        if (imgEl) image = imgEl.src;
      } else if (container.classList.contains('home')) {
        // Home section
        name = container.querySelector('h3').innerText;
        let imgEl = container.querySelector('.image img');
        if (imgEl) image = imgEl.src;
      }

      addToCart(name, price, image);
    })
  })

  updateCartUI();

  // Handle Order Form Submission
  let orderForm = document.querySelector('.order form');
  if (orderForm) {
    orderForm.addEventListener('submit', async (e) => {
      e.preventDefault();

      if (cart.length === 0) {
        alert("Your cart is empty! Add some food first.");
        return;
      }

      let name = orderForm.querySelector('input[type="text"]').value;
      let email = orderForm.querySelector('input[type="email"]').value;
      let phone = orderForm.querySelector('input[type="number"]').value;
      let address = orderForm.querySelector('textarea').value;

      if (!name || !email || !phone || !address) {
        alert("Please fill in all details");
        return;
      }

      let orderData = {
        customer: { name, email, phone, address },
        items: cart,
        total: cart.reduce((sum, item) => sum + (item.price * item.qty), 0)
      };

      try {
        let response = await fetch('http://localhost:3000/order', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(orderData)
        });

        let result = await response.json();
        if (result.success) {
          alert("Order placed successfully! Order ID: " + result.orderId);
          cart = [];
          updateCartUI();
          orderForm.reset();
          shoppingCartContainer.classList.remove('active');
        } else {
          alert("Something went wrong. Try again.");
        }
      } catch (err) {
        console.error(err);
        alert("Failed to connect to server. Is the backend running?");
      }
    });
  }
});
