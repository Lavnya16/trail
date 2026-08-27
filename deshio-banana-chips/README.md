# Banana Bliss Marketplace — Full Stack E-commerce Starter

This project is a complete marketplace-style starter for a banana chips brand.

## Included
- Responsive Flipkart/Meesho-style storefront
- Search
- Categories
- Sorting
- Product detail pages
- Product cards and discounts
- Wishlist
- User registration/login/logout
- Session shopping cart
- Quantity controls
- Checkout
- COD + demo UPI option
- Order database
- Customer order history
- Order detail and tracking timeline
- Admin dashboard
- Admin order status updates
- Inventory/stock management
- SQLite database
- Flask REST cart/wishlist endpoints

## Run on Windows
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

## Admin demo login
Email: admin@bananabliss.in
Password: Admin@123

CHANGE THIS PASSWORD/SECRET KEY BEFORE ANY PUBLIC DEPLOYMENT.

## Important production upgrades
This is a strong functional MVP, not a production payment platform. Before making it publicly accessible:
1. Deploy Flask behind Gunicorn/waitress + HTTPS.
2. Move SQLite to PostgreSQL/MySQL.
3. Add proper admin authentication/roles and CSRF protection.
4. Add Razorpay/Stripe/other real payment gateway and webhook verification.
5. Add email/SMS/WhatsApp order notifications.
6. Store real product images in object storage/CDN.
7. Add shipping integration, returns/refunds and GST/invoice logic as required.
8. Add rate limiting, secure cookies, input validation, logging, backups and monitoring.
9. Add a real domain and production environment variables.

## Suggested public AWS architecture
CloudFront + S3 (static assets) -> HTTPS Load Balancer / App Runner / ECS -> Flask API -> RDS PostgreSQL
                                      -> S3 product images
                                      -> SES/SNS notifications
                                      -> Razorpay webhook
