# ♻️ EcoRewards

EcoRewards is a gamified waste management system that incentivizes users to submit their waste responsibly. Users earn EcoPoints based on the type and quantity of waste submitted and can redeem these points for rewards like Amazon vouchers, eco-friendly products, or UPI cash.

---

## 🌟 Features

### ✅ User Panel
- 👤 User Login & Dashboard
- ♻️ Waste Submission (Type, Quantity, Location)
- 📊 Track Submission History with Approval Status
- 🪙 Earn & Track EcoPoints
- 🎁 Redeem EcoPoints for rewards

### ✅ Admin Panel
- 📋 View and Approve Waste Submissions
- 🏆 Manage Reward Catalog (Add, Activate/Deactivate, Set Stock & Points)
- 🧮 Define Point Rules per Waste Type
- 👥 View All Registered Users
- 📈 Track Total Points Distributed, Submissions, and Redemptions

---

## 📸 Screenshots

### 🎮 User Dashboard
![User Dashboard](https://github.com/shreeharini-261/ECO_Rewards/blob/main/images/user-dashboard.png)

### 🧾 Admin Dashboard
![Admin Dashboard](https://github.com/shreeharini-261/ECO_Rewards/blob/main/images/Screenshot%20from%202025-06-29%2020-18-26.png)

### 🎁 Rewards Management
![Rewards Panel](https://github.com/shreeharini-261/ECO_Rewards/blob/main/images/Screenshot%20from%202025-06-29%2020-18-31.png)

---

## 🏗️ Tech Stack

- 💻 Frontend: HTML, CSS, Bootstrap
- 🧠 Backend: Python (Flask)
- 🗃️ Database: SQLite
- 🔐 Authentication: Flask-Login

---

## 🔁 How It Works

1. 📤 User submits waste entry → Admin reviews and approves
2. 🎯 Points are allocated based on waste type & quantity
3. 🛍️ Points can be redeemed for real-world rewards
4. 🎉 Admin manages users, rewards, and monitors activity

---

## 🧪 Sample Point Rule Logic

| Waste Type | Points per kg |
|------------|----------------|
| Plastic    | 5 pts          |
| Metal      | 15 pts         |
| Organic    | 2 pts          |
| E-waste    | 20 pts         |

(Admins can modify these rules via the dashboard.)

---

## 🚀 Setup Instructions

```bash
# 1. Clone the repo
git clone https://github.com/your-username/ecorewards.git
cd ecorewards

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
python app.py
