# VENOM Shop Management System

VENOM Shop is a comprehensive, locally-hosted web application designed to manage the inventory, sales, and specialized laser material operations for a small shop or business. Built with Python and the NiceGUI framework, it offers an intuitive Arabic/English interface with real-time analytics, chatbot assistance, and dedicated modules for general products and laser machine materials.

![VENOM Shop Screenshot](png.png)

## 🌟 Features

*   **Interactive Dashboard**: Real-time analytics displaying total revenue, net profit, product count, order volume, and low-stock alerts.
*   **Product Management**:
    *   Add, edit, and delete products with purchase/sale prices and stock levels.
    *   View a sortable, searchable table of all products.
    *   Get low-stock warnings.
*   **Order Processing**:
    *   Easily create new sales orders by selecting a product and customer.
    *   View real-time pricing and profit calculations.
    *   Access a scrollable history of recent orders.
*   **Laser Material Management (Specialized Module)**:
    *   **Dedicated Tabs**: Manage materials, add new ones, process transactions (purchase, sale, return, waste), and view history.
    *   **Advanced Analytics**: Track net profit, material waste, and total purchases specific to laser operations.
    *   **Profit Margin Preview**: See profit calculations instantly when setting prices for new materials.
    *   **Comprehensive Transaction History**: Filter and review all material-related activities with detailed notes and timestamps.
*   **AI-Powered Assistance**:
    *   Integrated ChatBot for user queries (falls back to a local version if API is unavailable).
    *   Accessible via a floating button on every page.
*   **Automatic Browser Launch**: Opens the default web browser to the home page upon startup for convenience.

## 🛠️ Technologies Used

*   **Frontend & Backend Framework**: [NiceGUI](https://nicegui.io/) (Python)
*   **Database**: SQLite (via a custom `DatabaseHandler`)
*   **AI Chatbot**: Custom `ChatBot` / `LocalChatBot` classes
*   **UI Components**: Quasar Framework (integrated with NiceGUI)

## 🚀 Getting Started

### Prerequisites

*   Python 3.8 or higher
*   pip (Python package installer)

### Installation

1.  Clone this repository or download the source code.
2.  Navigate to the project directory in your terminal.
3.  Install the required dependencies.
    ```bash
    pip install -r requirements.txt
    ```
### Running the Application

1.  Make sure you are in the project's root directory.
2.  Execute the main script:
    ```bash
    python app.py
    ```
3.  The application will start a local server on `http://127.0.0.1:8080` and automatically open your default web browser to the home page.

## 🤖 ChatBot Configuration
1. Go to [OpenRouter](https://openrouter.ai/)
2. Create your API key and copy it.
3. Place it in the `.env` file

## 📜 License

This project is for educational and demonstration purposes.

