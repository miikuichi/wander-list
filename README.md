# 🦸 PisoHeroes

> **Every Peso Counts.** A comprehensive personal finance and budgeting application designed to turn users into heroes of their own financial journey.

[![Django](https://img.shields.io/badge/Django-5.2.6-092E20?style=for-the-badge&logo=django)](https://www.djangoproject.com/)
[![Supabase](https://img.shields.io/badge/Supabase-Auth_&_DB-3ECF8E?style=for-the-badge&logo=supabase)](https://supabase.com/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5-7952B3?style=for-the-badge&logo=bootstrap)](https://getbootstrap.com/)
[![Status](https://img.shields.io/badge/Development-Sprint_5-blue?style=for-the-badge)](https://github.com/)

---

## 📖 Table of Contents
- [About the Project](#-about-the-project)
- [Key Features](#-key-features)
- [Tech Stack](#-tech-stack)
- [Project Context](#-project-context)
- [The Team](#-the-team)
- [Installation & Setup](#-installation--setup)
- [Environment Variables](#-environment-variables)
- [License](#-license)

---

## 💡 About the Project

**PisoHeroes** is a web-based financial management tool that helps users track expenses, set budget limits, and achieve savings goals. Built with a robust **Django** backend and integrated with **Supabase** for secure authentication and data handling, the application offers a real-time dashboard to monitor financial health.

Whether you are saving for a dream vacation or just trying to stick to a daily allowance, PisoHeroes provides the insights needed to stay on track.

---

## ✨ Key Features

💸 **Smart Dashboard**
* Real-time calculation of **Daily Allowance** based on your monthly budget.
* Visual breakdown of expenses for the day, week, and month.

📉 **Expense Tracking**
* Log expenses with specific categories.
* View spending history and trends.

🚨 **Budget Alerts**
* Set spending limits for specific categories (e.g., Food, Transport).
* Receive **intelligent notifications** when you approach or exceed your budget thresholds.

🎯 **Savings Goals**
* Create custom savings targets (e.g., "New Laptop").
* Track progress with visual percentage bars.
* Archive completed goals or reset progress as needed.

🔔 **Reminders & Notifications**
* Set due dates for bills or financial tasks.
* Get email notifications and on-site alerts for critical updates.

---

## 🛠 Tech Stack

**Backend**
* **Framework:** Django 5.2.6 (Python)
* **Database & Auth:** Supabase (PostgreSQL)
* **ORM:** Django ORM & Supabase Python Client

**Frontend**
* **Styling:** Bootstrap 5, Custom CSS
* **Templating:** Django Template Language (DTL)

**Deployment & Tools**
* **Host:** Render
* **Static Files:** WhiteNoise
* **Environment Management:** python-dotenv

---

## 🎓 Project Context

This application was developed as a comprehensive project for the following subjects:

* **IT317:** Project Management for IT
* **CSIT327:** Information Management 2

The development followed an **Agile/Scrum methodology**, executed over **5 Sprints** within a single academic semester.

---

## 👥 The Team

### 💻 Development Team
| Role | Name |
|:--- |:--- |
| **Lead Developer** | **Michael Sevilla** |
| Developer | Christian Kyle Tapales |
| Developer | Jeff Seloterio |

### 📅 Project Management Team
| Role | Name |
|:--- |:--- |
| **Product Owner** | **Justin Wolfe** |
| **Scrum Master** | **Sharbelle Temperatura** |
| **Business Analyst** | **Dillan Ycoy** |

---

## ⚙️ Installation & Setup

Follow these steps to run the project locally.

### 1. Clone the Repository
```bash
git clone [https://github.com/your-username/wander-list.git](https://github.com/your-username/wander-list.git)
cd wander-list
```
### 2. Create a Virtual Environment
```Bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```
### 3. Install Dependencies
```Bash
pip install -r requirements.txt
```
### 4. Configure Environment Variables
Create a .env file in the root directory (refer to the Environment Variables section below).

### 5. Run Migrations
```Bash
python manage.py migrate
```
### 6. Start the Server
```Bash
python manage.py runserver
Visit http://127.0.0.1:8000 in your browser.
```
