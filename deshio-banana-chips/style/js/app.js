
async function cartApi(product_id, action, quantity=1){
  const r=await fetch('/api/cart',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({product_id,action,quantity})});
  const d=await r.json(); if(!d.ok){toast(d.error||'Could not update cart');return null}
  const c=document.getElementById('cartCount'); if(c)c.textContent=d.count;
  toast('Cart updated'); return d;
}
function addToCart(id,qty=1){cartApi(id,'add',qty)}
function changeQty(id,action){cartApi(id,action).then(d=>{if(d)location.reload()})}
async function toggleWish(id,btn){
  const r=await fetch('/api/wishlist/'+id,{method:'POST'}); const d=await r.json();
  if(r.status===401){location.href='/login';return}
  if(d.ok){btn.textContent=d.active?'♥':'♡';toast(d.active?'Added to wishlist':'Removed from wishlist')}
}
function toast(m){const t=document.getElementById('toast');t.textContent=m;t.classList.add('show');clearTimeout(window.__toast);window.__toast=setTimeout(()=>t.classList.remove('show'),2200)}
setTimeout(()=>document.querySelectorAll('.flash').forEach(x=>x.remove()),3500);
