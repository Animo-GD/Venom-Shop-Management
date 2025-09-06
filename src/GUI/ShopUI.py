from nicegui import ui
import asyncio
from src.database.DatabaseHandler import DatabaseHandler
import json
from src.ChatBot.ChatBot import ChatBot

db = DatabaseHandler()
chatbot = ChatBot()
class ShopUI:
    def __init__(self):
        self.current_page = "home"
        self.chat_visible = False
        self.chat_messages = []  # Store chat history

    def create_header(self):
        """Create the header with logo and navigation"""
        with ui.header().classes('bg-gradient-to-r from-purple-600 to-blue-600 text-white shadow-lg'):
            with ui.row().classes('w-full items-center justify-between px-4'):
                ui.label('🐍 VENOM').classes('text-2xl font-bold')
                with ui.row().classes('gap-2'):
                    ui.button('🏠 الرئيسية', on_click=lambda: self.show_page('home')).classes('bg-transparent hover:bg-white/20')
                    ui.button('➕ اضافة منتج', on_click=lambda: self.show_page('add_product')).classes('bg-transparent hover:bg-white/20')
                    ui.button('🛒 بيع منتج', on_click=lambda: self.show_page('take_order')).classes('bg-transparent hover:bg-white/20')
                    ui.button('📦 إدارة المنتجات', on_click=lambda: self.show_page('manage_products')).classes('bg-transparent hover:bg-white/20')
                    ui.button('⚡ مكينة الليزر', on_click=lambda: self.show_page('laser_management')).classes('bg-transparent hover:bg-white/20')

    def show_page(self, page_name: str):
        self.current_page = page_name
        ui.navigate.to(f'/{page_name}')

    def create_chat_button(self):
        chat_button = ui.button('💬', on_click=self.toggle_chat).classes(
            'fixed bottom-4 right-4 z-50 bg-blue-500 hover:bg-blue-600 text-white rounded-full w-16 h-16 text-2xl shadow-lg'
        )
        return chat_button

    def toggle_chat(self):
        self.chat_visible = not self.chat_visible
        if hasattr(self, 'chat_container'):
            self.chat_container.visible = self.chat_visible

    def create_chat_interface(self):
        with ui.card().classes('fixed bottom-20 right-4 w-80 h-96 z-40 shadow-xl').bind_visibility_from(self, 'chat_visible') as chat_container:
            self.chat_container = chat_container
            ui.label('🤖 أسامة - مساعد المحل').classes('text-lg font-bold text-center text-blue-600 p-2')
            
            with ui.scroll_area().classes('h-64 border rounded p-2 bg-gray-50 mb-2') as chat_area:
                self.chat_area = chat_area
                # Add welcome message
                with self.chat_area:
                    ui.label('أسامة: أهلاً! اسأل عن أي حاجة في المحل 😊').classes('text-gray-700 mb-2 p-2 bg-blue-50 rounded')
            
            with ui.row().classes('w-full gap-2'):
                chat_input = ui.input(placeholder='اسأل عن أي حاجة في المحل...').classes('flex-1')
                send_btn = ui.button('ابعت', on_click=lambda: asyncio.create_task(self.send_message(chat_input))).classes('bg-blue-500 text-white')
                
                # Allow Enter key to send message
                chat_input.on('keydown.enter', lambda: asyncio.create_task(self.send_message(chat_input)))

    async def send_message(self, input_field):
        message = input_field.value.strip() if input_field.value else ''
        if not message:
            return

        input_field.value = ''

        # Add user message to chat
        with self.chat_area:
            ui.label(f"أنت: {message}").classes('text-blue-600 font-semibold mb-2 p-2 bg-blue-100 rounded')

        # Show loading message
        with self.chat_area:
            loading_label = ui.label('أسامة: جاري التفكير... ⏳').classes('text-gray-500 italic mb-2')

        try:
            products = db.get_all_products()
            orders = db.get_all_orders()
            analytics = db.get_analytics_data()
            
            # Add laser data
            laser_materials = db.get_all_laser_materials()
            laser_transactions = db.get_laser_transactions()
            laser_analytics = db.get_laser_analytics()

            # Create comprehensive context
            context = {
                "main_shop": {
                    "products_count": len(products),
                    "orders_count": len(orders),
                    "total_revenue": f"{analytics['total_revenue']:.2f}",
                    "total_profit": f"{analytics['total_profit']:.2f}",
                    "low_stock_products": [p['name'] for p in products if p['stock'] < 10],
                    "recent_orders": [{"customer": o['name'], "product": o['product_name'], 
                                    "quantity": o['quantity'], "date": o['date'], "total": o['total_price']} 
                                for o in orders[:10]],
                },
                "laser": {
                    "materials_count": len(laser_materials),
                    "transactions_count": len(laser_transactions),
                    "total_purchases": f"{laser_analytics['total_purchases']:.2f}",
                    "net_sales": f"{laser_analytics['net_sales']:.2f}",
                    "net_profit": f"{laser_analytics['net_profit']:.2f}",
                    "total_waste": f"{laser_analytics['total_waste']:.2f}",
                    "recent_materials": [{"name": m['name'], "side": m['material_side'], 
                                        "stock": m['stock_quantity'], "sale_price": m['sale_price']} 
                                    for m in laser_materials[:5]],
                }
            }

            # Get AI response
            context_str = json.dumps(context, ensure_ascii=False, indent=2)
            reply = await chatbot.get_response(message=message, context=context_str)

            # Remove loading message
            loading_label.delete()

            # Add AI response to chat
            with self.chat_area:
                ui.label(f"أسامة: {reply}").classes('text-gray-700 mb-4 p-2 bg-gray-100 rounded')

            # Auto-scroll to bottom
            self.chat_area.scroll_to(percent=1.0)

        except Exception as e:
            # Remove loading message and show error
            loading_label.delete()
            with self.chat_area:
                ui.label(f"أسامة: ❌ حدث خطأ: {str(e)}").classes('text-red-600 mb-4 p-2 bg-red-50 rounded')

