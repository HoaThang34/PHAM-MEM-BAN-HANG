let cart = [];

function filterProducts() {
    const query = document.getElementById("search").value.trim().toLowerCase();
    if (!query) {
        // Hiển thị tất cả nếu ô trống
        document.querySelectorAll(".product-card").forEach(card => card.style.display = "block");
        return;
    }

    const cards = document.querySelectorAll(".product-card");
    cards.forEach(card => {
        const name = card.querySelector("h3").textContent.toLowerCase();
        const barcode = card.querySelector(".barcode").textContent;
        // Tìm theo tên hoặc mã vạch
        const match = name.includes(query) || barcode.includes(query);
        card.style.display = match ? "block" : "none";
    });
}

function scanBarcode() {
    const code = prompt("Nhập mã vạch:");
    if (!code) return;
    const cards = document.querySelectorAll(".product-card");
    let found = false;
    cards.forEach(card => {
        const barcode = card.querySelector(".barcode").textContent;
        if (barcode === code) {
            card.click();
            found = true;
        }
    });
    if (!found) alert("Không tìm thấy sản phẩm có mã vạch này.");
}

function addToCart(id, name, price, stock) {
    if (stock <= 0) {
        alert("Hết hàng!");
        return;
    }
    const item = cart.find(x => x.id === id);
    if (item) {
        if (item.qty >= stock) {
            alert("Không đủ hàng trong kho!");
            return;
        }
        item.qty++;
    } else {
        cart.push({id, name, price, qty: 1});
    }
    renderCart();
}

function renderCart() {
    const cartEl = document.getElementById("cart-items");
    cartEl.innerHTML = "";
    let total = 0;
    cart.forEach(item => {
        const div = document.createElement("div");
        div.className = "cart-item";
        div.innerHTML = `
            <span>${item.name} x${item.qty}</span>
            <span>${Math.round(item.price * item.qty)}đ</span>
            <button onclick="removeOne(${item.id})">-</button>
        `;
        cartEl.appendChild(div);
        total += item.price * item.qty;
    });
    document.getElementById("total").textContent = Math.round(total);
}

function removeOne(id) {
    const item = cart.find(x => x.id === id);
    if (item) {
        item.qty--;
        if (item.qty <= 0) cart = cart.filter(x => x.id !== id);
        renderCart();
    }
}

function checkout() {
    if (cart.length === 0) return alert("Giỏ hàng trống!");
    const customer_name = document.getElementById("customer_name").value;
    const customer_phone = document.getElementById("customer_phone").value;
    fetch("/create_order", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({cart, customer_name, customer_phone})
    })
    .then(r => r.json())
    .then(data => {
        if (data.error) {
            alert("Lỗi: " + data.error);
        } else {
            window.location.href = `/order/${data.order_id}`;
        }
    });
}