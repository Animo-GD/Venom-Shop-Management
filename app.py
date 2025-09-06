from nicegui import ui, app
from src.database.DatabaseHandler import DatabaseHandler
from src.ChatBot.ChatBot import ChatBot,LocalChatBot
from src.GUI.ShopUI import ShopUI
from datetime import datetime
import logging



db = DatabaseHandler()
try:
    chatbot = ChatBot()
    
    if chatbot.api_key and not chatbot.test_connection():
        print("⚠️ Warning: ChatBot API connection test failed, using local chatbot")
        chatbot = LocalChatBot()
    elif not chatbot.api_key:
        print("ℹ️ No API key found, using local chatbot")
        chatbot = LocalChatBot()
except Exception as e:
    print(f"⚠️ ChatBot initialization failed, using local chatbot: {e}")
    chatbot = LocalChatBot()


shop_ui = ShopUI()


@ui.page('/')
@ui.page('/home')
def home_page():
    """Home page with analytics dashboard"""
    shop_ui.create_header()

    with ui.column().classes('p-6 max-w-6xl mx-auto items-center'):
        ui.label('📊 لوحة التحكم').classes('text-4xl font-bold text-center text-gray-900 mb-8')

        analytics = db.get_analytics_data()

        with ui.row().classes('gap-6 w-full mb-8 justify-center'):
            
            with ui.card().classes('p-6 bg-gradient-to-br from-green-400 to-green-600 text-white flex-2 shadow-lg rounded-xl'):
                ui.icon('account_balance_wallet', size='2.5rem')
                ui.label(f"{analytics['total_revenue']:.2f} جنيه").classes('text-3xl font-bold text-center')
                ui.label('إجمالي الدخل').classes('text-green-100 text-center')

            
            with ui.card().classes('p-6 bg-gradient-to-br from-emerald-400 to-emerald-600 text-white flex-2 shadow-lg rounded-xl'):
                ui.icon('trending_up', size='2.5rem')
                ui.label(f"{analytics['total_profit']:.2f} جنيه").classes('text-3xl font-bold text-center')
                ui.label('صافي الربح').classes('text-emerald-100 text-center')

            
            if analytics['total_loss'] > 0:
                with ui.card().classes('p-6 bg-gradient-to-br from-red-400 to-red-600 text-white flex-2 shadow-lg rounded-xl'):
                    ui.icon('trending_down', size='2.5rem')
                    ui.label(f"{analytics['total_loss']:.2f} جنيه").classes('text-3xl font-bold text-center')
                    ui.label('إجمالي الخسارة (بيع تحت التكلفة)').classes('text-red-100 text-center')

            
            with ui.card().classes('p-6 bg-gradient-to-br from-purple-400 to-purple-600 text-white flex-2 shadow-lg rounded-xl'):
                ui.icon('inventory', size='2.5rem')
                ui.label(f"{analytics['products_count']}").classes('text-3xl font-bold text-center')
                ui.label('عدد المنتجات').classes('text-purple-100 text-center')

            
            with ui.card().classes('p-6 bg-gradient-to-br from-blue-400 to-blue-600 text-white flex-2 shadow-lg rounded-xl'):
                ui.icon('shopping_cart', size='2.5rem')
                ui.label(f"{analytics['total_orders']}").classes('text-3xl font-bold text-center')
                ui.label('عدد الطلبات').classes('text-blue-100 text-center')

            
            with ui.card().classes('p-6 bg-gradient-to-br from-amber-400 to-amber-600 text-white flex-2 shadow-lg rounded-xl'):
                ui.icon('warning', size='2.5rem')
                ui.label(f"{analytics['low_stock_count']}").classes('text-3xl font-bold text-center')
                ui.label('منتجات قربت تخلص').classes('text-amber-100 text-center')

        
        with ui.card().classes('p-6 rounded-xl shadow-md'):
            ui.label('🔥 المنتجات الأكثر مبيعًا').classes('text-xl font-bold text-gray-900 mb-4 text-center')
            if analytics['top_products']:
                for product in analytics['top_products']:
                    with ui.row().classes('justify-between items-center py-2 border-b'):
                        ui.label(product['name']).classes('font-medium')
                        ui.label(f"{product['sold']} قطعة").classes('text-green-600 font-bold')
            else:
                ui.label('لا توجد بيانات مبيعات حالياً').classes('text-gray-500 italic text-center')

    shop_ui.create_chat_button()
    shop_ui.create_chat_interface()


@ui.page('/add_product')
def add_product_page():
    """Add product page"""
    shop_ui.create_header()

    with ui.column().classes('p-6 max-w-2xl mx-auto'):
        ui.label('➕ اضافة منتج جديد').classes('text-3xl font-bold text-gray-800 mb-6')

        with ui.card().classes('p-8'):
            existing_products = [p['name'] for p in db.get_all_products()]

            name_input = ui.input('اسم المنتج (Product Name)').classes('w-full mb-4')
            name_input.props('outlined dense')
            with name_input.add_slot('append'):
                ui.icon('search')

            purchase_input = ui.number('سعر الشراء', format='%.2f').classes('w-full mb-4')
            purchase_input.props('outlined dense')

            sale_input = ui.number('سعر البيع', format='%.2f').classes('w-full mb-4')
            sale_input.props('outlined dense')

            stock_input = ui.number('الكمية المتوفرة', format='%.0f').classes('w-full mb-4')
            stock_input.props('outlined dense')

            def add_product_action():
                if not all([name_input.value, purchase_input.value is not None, sale_input.value is not None, stock_input.value is not None]):
                    ui.notify('سايب مكان فاضي ليه؟', color='negative')
                    return

                if name_input.value in existing_products:
                    ui.notify('المنتج ده موجود فعلا, دوس تحديث للمنتج', color='negative')
                    return

                nm = name_input.value.strip()
                success = db.add_product(
                    nm,
                    float(purchase_input.value),
                    float(sale_input.value),
                    int(stock_input.value),
                )

                if success:
                    existing_products.append(nm)
                    ui.notify('تم اضافة المنتج بنجاح', color='positive')
                    name_input.value = ''
                    purchase_input.value = None
                    sale_input.value = None
                    stock_input.value = None
                else:
                    ui.notify('حصل مشكلة وانا بضيف المنتج, جرب تاني', color='negative')

            ui.button('اضافة منتج', on_click=add_product_action).classes(
                'w-full bg-green-500 hover:bg-green-600 text-white py-3 text-lg font-semibold'
            )

        
        with ui.card().classes('p-4 mt-4 w-full max-w-2xl'):
            ui.label('📦 المنتجات الحالية').classes('text-xl font-bold text-gray-800 mb-4')

            products = db.get_all_products()
            if products:
                with ui.scroll_area().classes('h-64'):
                    for product in products:
                        with ui.row().classes('justify-between items-center py-2 border-b w-full'):
                            with ui.column().classes('flex-1'):
                                ui.label(product['name']).classes('font-semibold')
                                ui.label(f"سعر الشراء: جنيه{product['purchase_price']:.2f} | سعر البيع: جنيه{product['sale_price']:.2f}").classes('text-sm text-gray-600')
                            stock_class = 'text-red-500' if product['stock'] < 10 else 'text-green-500'
                            ui.label(f"الكمية المتوفرة: {product['stock']}").classes(f'font-bold {stock_class}')
            else:
                ui.label('المحل قحطان مفيش بضاعة').classes('text-gray-500 italic text-center')

    shop_ui.create_chat_button()
    shop_ui.create_chat_interface()


@ui.page('/take_order')
def take_order_page():
    """Take order page"""
    shop_ui.create_header()

    with ui.column().classes('p-6 max-w-2xl mx-auto'):
        ui.label('🛒 اخراج طلب من البضاعة').classes('text-3xl font-bold text-gray-800 mb-6')

        with ui.card().classes('p-8'):
            products = db.get_all_products()
            product_options = [p['name'] for p in products]

            product_select = ui.select(
                options=product_options,
                label='Select Product',
                with_input=True,
            ).classes('w-full mb-4')
            product_select.props('outlined dense use-input')

            customer_name = ui.input('اسم العميل (Customer Name)').classes('w-full mb-4')
            customer_name.props('outlined dense')

            quantity_input = ui.number('الكمية', format='%.0f', value=1).classes('w-full mb-4')
            quantity_input.props('outlined dense')

            product_info = ui.label('اختار منتج علشان تشوف تفاصيله').classes('text-gray-600 mb-4')

            def update_product_info():
                if product_select.value and product_select.value in product_options:
                    product = db.get_product_by_name(product_select.value)
                    if product:
                        total = (product['sale_price'] or 0) * (quantity_input.value or 0)
                        unit_profit = (product['sale_price'] or 0) - (product['purchase_price'] or 0)
                        product_info.text = (
                            f"سعر البيع: جنيه{product['sale_price']:.2f} | سعر الشراء: جنيه{product['purchase_price']:.2f} | "
                            f"ربح/قطعة: جنيه{unit_profit:.2f} | الكلي: جنيه{total:.2f} | المتوفر: {product['stock']}"
                        )
                        product_info.classes('text-blue-600 font-semibold mb-4')
                    else:
                        product_info.text = 'المنتج غير متوفر'
                        product_info.classes('text-red-600 mb-4')
                else:
                    product_info.text = 'اختار منتج علشان تشوف تفاصيله'
                    product_info.classes('text-gray-600 mb-4')

            product_select.on('update:model-value', update_product_info)
            quantity_input.on('update:model-value', update_product_info)

            def place_order():
                if not all([product_select.value, customer_name.value, quantity_input.value]):
                    ui.notify('أبوس ايدك املي كل الخانات, ماتسيبش حاجة فاضية', color='negative')
                    return

                product = db.get_product_by_name(product_select.value)
                if not product:
                    ui.notify('المنتج غير متاح', color='negative')
                    return

                quantity = int(quantity_input.value)
                if product['stock'] < quantity:
                    ui.notify(f"الكمية المطلوبة غير متوفرة حاليا! مفيش غير {product['stock']} متاح.", color='negative')
                    return

                
                order_success = db.add_order(
                    product_id=product['id'],
                    name=customer_name.value.strip(),
                    quantity=quantity,
                )

                if order_success:
                    total_price = product['sale_price'] * quantity
                    ui.notify(f'تم تسجيل الطلب بنجاح: جنيه{total_price:.2f}', color='positive')
                    product_select.value = None
                    customer_name.value = ''
                    quantity_input.value = 1
                    update_product_info()

                    
                    updated_products = db.get_all_products()
                    product_select.options = [p['name'] for p in updated_products]
                else:
                    ui.notify('حصل مشكلة في اخراج الطلب', color='negative')

            ui.button('قم بسحب البضاعة', on_click=place_order).classes(
                'w-full bg-blue-500 hover:bg-blue-600 text-white py-3 text-lg font-semibold'
            )

        
        with ui.card().classes('p-4 mt-4 w-full max-w-2xl'):
            ui.label('📋  قائمة السحب').classes('text-xl font-bold text-gray-800 mb-4')

            orders = db.get_all_orders()[-10:]  
            if orders:
                with ui.scroll_area().classes('h-40 w-100'):
                    for order in reversed(orders):
                        with ui.row().classes('justify-between items-center py-3 border-b w-full'):
                            with ui.column().classes('flex-1'):
                                ui.label(f"{order['name']} - {order['product_name']}").classes('font-semibold')
                                ui.label(
                                    f"الكمية: {order['quantity']} | جنيه{order['total_price']:.2f}"
                                ).classes('text-sm text-gray-600')
                            ui.label(str(order['date']).split()[0]).classes('text-xs text-gray-500')
            else:
                ui.label('مفيش أوردارات حاليا, حد بصلنا فيها').classes('text-gray-500 italic text-center')

    shop_ui.create_chat_button()
    shop_ui.create_chat_interface()

@ui.page('/manage_products')
def manage_products_page():
    """Manage products page"""
    shop_ui.create_header()
    
    with ui.column().classes('p-6 max-w-6xl mx-auto'):
        ui.label('📦 إدارة المنتجات').classes('text-3xl font-bold text-gray-800 mb-6')

        products = db.get_all_products()
        if not products:
            with ui.card().classes('p-8 text-center'):
                ui.label('🚫 لا يوجد منتجات في المخزن حالياً').classes('text-red-500 italic text-xl')
            return

        rows = []
        for p in products:
            rows.append({
                'id': p['id'],
                'name': p['name'],
                'purchase_price': f"{p['purchase_price']:.2f}",
                'sale_price': f"{p['sale_price']:.2f}",
                'stock': p['stock'],
            })

        columns = [
            {'name': 'id', 'label': 'ID', 'field': 'id', 'required': True, 'align': 'center'},
            {'name': 'name', 'label': 'اسم المنتج', 'field': 'name', 'required': True, 'align': 'left'},
            {'name': 'purchase_price', 'label': 'سعر الشراء (جنيه)', 'field': 'purchase_price', 'required': True, 'align': 'center'},
            {'name': 'sale_price', 'label': 'سعر البيع (جنيه)', 'field': 'sale_price', 'required': True, 'align': 'center'},
            {'name': 'stock', 'label': 'المخزون', 'field': 'stock', 'required': True, 'align': 'center'},
            {'name': 'actions', 'label': 'إجراءات', 'field': 'actions', 'required': True, 'align': 'center'},
        ]

        def edit_product_dialog(product_id):
            current_products = db.get_all_products()
            product = next((p for p in current_products if p['id'] == product_id), None)
            if not product:
                ui.notify('❌ المنتج غير موجود', color='negative')
                return

            with ui.dialog() as dialog, ui.card().classes('p-6 w-96'):
                ui.label(f"✏️ تعديل {product['name']}").classes('text-lg font-bold mb-4')

                name_edit = ui.input('اسم المنتج', value=product['name']).classes('mb-2 w-full')
                purchase_edit = ui.number('سعر الشراء', value=product['purchase_price']).classes('mb-2 w-full')
                sale_edit = ui.number('سعر البيع', value=product['sale_price']).classes('mb-2 w-full')
                stock_edit = ui.number('الكمية', value=product['stock']).classes('mb-4 w-full')

                def save_changes():
                    success = db.update_product(
                        product_id=product['id'],
                        name=name_edit.value,
                        purchase_price=purchase_edit.value,
                        sale_price=sale_edit.value,
                        stock=stock_edit.value,
                    )
                    if success:
                        ui.notify('✅ تم تعديل المنتج بنجاح', color='positive')
                        dialog.close()
                        ui.navigate.reload()
                    else:
                        ui.notify('❌ حصلت مشكلة أثناء التعديل', color='negative')

                with ui.row().classes('gap-2 w-full'):
                    ui.button('💾 حفظ', on_click=save_changes).classes('bg-blue-500 text-white flex-1')
                    ui.button('❌ إلغاء', on_click=dialog.close).classes('bg-gray-500 text-white flex-1')

            dialog.open()

        def delete_product_dialog(product_id):
            current_products = db.get_all_products()
            product = next((p for p in current_products if p['id'] == product_id), None)
            if not product:
                ui.notify('❌ المنتج غير موجود', color='negative')
                return

            def confirm_delete():
                success = db.remove_product(product['id'])
                if success:
                    ui.notify('🗑️ تم حذف المنتج', color='positive')
                    dialog.close()
                    ""
                    ui.navigate.reload()
                else:
                    ui.notify('❌ فشل الحذف', color='negative')

            with ui.dialog() as dialog, ui.card().classes('p-6 w-80'):
                ui.label(f"⚠️ هل أنت متأكد من حذف {product['name']}؟").classes('text-red-600 mb-4 text-center')
                with ui.row().classes('gap-2 w-full'):
                    ui.button('✅ نعم, احذف', on_click=confirm_delete).classes('bg-red-500 text-white flex-1')
                    ui.button('❌ إلغاء', on_click=dialog.close).classes('bg-gray-300 text-black flex-1')

            dialog.open()

        
        table = ui.table(
            columns=columns,
            rows=rows,
            row_key='id'
        ).classes('w-full shadow-lg')

        
        table.add_slot('body-cell-actions', '''
            <q-td :props="props">
                <q-btn flat round dense 
                       @click="$parent.$emit('edit', props.row)" 
                       icon="edit" 
                       color="orange" 
                       size="sm">
                    <q-tooltip>تعديل</q-tooltip>
                </q-btn>
                <q-btn flat round dense 
                       @click="$parent.$emit('delete', props.row)" 
                       icon="delete" 
                       color="red" 
                       size="sm">
                    <q-tooltip>حذف</q-tooltip>
                </q-btn>
            </q-td>
        ''')

        
        table.on('edit', lambda e: edit_product_dialog(e.args['id']))
        table.on('delete', lambda e: delete_product_dialog(e.args['id']))

        
        with ui.row().classes('mt-4 gap-4 justify-center'):
            low_stock_products = [p for p in products if p['stock'] < 10]
            if low_stock_products:
                with ui.card().classes('p-4 bg-red-50 border-l-4 border-red-500'):
                    ui.label('⚠️ تحذير: منتجات قاربت على النفاد').classes('text-red-700 font-bold')
                    for product in low_stock_products:
                        ui.label(f"• {product['name']}: {product['stock']} قطعة فقط").classes('text-red-600')
@ui.page('/laser_management')
def laser_management_page():
    """Laser machine management page"""
    shop_ui.create_header()
    
    with ui.column().classes('p-6 max-w-7xl mx-auto'):
        ui.label('⚡ إدارة مكينة الليزر').classes('text-3xl font-bold text-gray-800 mb-6')
        
        
        analytics = db.get_laser_analytics()
        
        with ui.row().classes('gap-4 w-full mb-6 justify-center flex-wrap'):
            
            with ui.card().classes('p-4 bg-gradient-to-br from-blue-400 to-blue-600 text-white flex-1 min-w-48 shadow-lg'):
                ui.icon('shopping_cart', size='2rem')
                ui.label(f"{analytics['total_purchases']:.2f} جنيه").classes('text-2xl font-bold')
                ui.label('إجمالي شراء الخامات').classes('text-blue-100')
            
            
            with ui.card().classes('p-4 bg-gradient-to-br from-green-400 to-green-600 text-white flex-1 min-w-48 shadow-lg'):
                ui.icon('sell', size='2rem')
                ui.label(f"{analytics['net_sales']:.2f} جنيه").classes('text-2xl font-bold')
                ui.label('صافي المبيعات').classes('text-green-100')
            
            
            profit_color = 'emerald' if analytics['net_profit'] >= 0 else 'red'
            icon_name = 'trending_up' if analytics['net_profit'] >= 0 else 'trending_down'
            with ui.card().classes(f'p-4 bg-gradient-to-br from-{profit_color}-400 to-{profit_color}-600 text-white flex-1 min-w-48 shadow-lg'):
                ui.icon(icon_name, size='2rem')
                ui.label(f"{analytics['net_profit']:.2f} جنيه").classes('text-2xl font-bold')
                ui.label('المكسب/الخسارة').classes(f'text-{profit_color}-100')
            
            
            with ui.card().classes('p-4 bg-gradient-to-br from-red-400 to-red-600 text-white flex-1 min-w-48 shadow-lg'):
                ui.icon('delete', size='2rem')
                ui.label(f"{analytics['total_waste']:.2f} جنيه").classes('text-2xl font-bold')
                ui.label('قيمة الفاقد').classes('text-red-100')
            
            
            with ui.card().classes('p-4 bg-gradient-to-br from-purple-400 to-purple-600 text-white flex-1 min-w-48 shadow-lg'):
                ui.icon('inventory_2', size='2rem')
                ui.label(f"{analytics['materials_count']}").classes('text-2xl font-bold')
                ui.label('أنواع الخامات').classes('text-purple-100')
        
        
        with ui.tabs().classes('w-full') as tabs:
            materials_tab = ui.tab('الخامات')
            add_material_tab = ui.tab('إضافة خامة')
            transaction_tab = ui.tab('بيع/شراء/استرجاع')
            history_tab = ui.tab('السجل')
        
        with ui.tab_panels(tabs, value=materials_tab).classes('w-full'):
            
            with ui.tab_panel(materials_tab):
                ui.label('📦 إدارة الخامات المتوفرة').classes('text-xl font-bold mb-4')
                
                materials = db.get_all_laser_materials()
                if materials:
                    
                    columns = [
                        {'name': 'id', 'label': 'ID', 'field': 'id', 'required': True, 'align': 'center'},
                        {'name': 'name', 'label': 'اسم الخامة', 'field': 'name', 'required': True, 'align': 'left'},
                        {'name': 'material_side', 'label': 'النوع', 'field': 'material_side', 'align': 'center'},
                        {'name': 'stock_quantity', 'label': 'الكمية المتوفرة', 'field': 'stock_quantity', 'align': 'center'},
                        {'name': 'purchase_price', 'label': 'سعر الشراء', 'field': 'purchase_price', 'align': 'center'},
                        {'name': 'sale_price', 'label': 'سعر البيع', 'field': 'sale_price', 'align': 'center'},
                        {'name': 'profit_margin', 'label': 'هامش الربح', 'field': 'profit_margin', 'align': 'center'},
                        {'name': 'actions', 'label': 'إجراءات', 'field': 'actions', 'align': 'center'},
                    ]
                    
                    rows = []
                    for material in materials:
                        stock_status = '🔴' if material['stock_quantity'] < 10 else '🟢'
                        profit_margin = material['sale_price'] - material['purchase_price']
                        profit_percent = (profit_margin / material['purchase_price'] * 100) if material['purchase_price'] > 0 else 0
                        
                        rows.append({
                            'id': material['id'],
                            'name': f"{stock_status} {material['name']}",
                            'material_side': material['material_side'],
                            'stock_quantity': f"{material['stock_quantity']:.0f}",
                            'purchase_price': f"{material['purchase_price']:.2f} جنيه",
                            'sale_price': f"{material['sale_price']:.2f} جنيه",
                            'profit_margin': f"{profit_margin:.2f} ({profit_percent:.1f}%)",
                        })
                    
                    table = ui.table(columns=columns, rows=rows, row_key='id').classes('w-full shadow-lg')
                    
                    def edit_material_dialog(material_id):
                        current_materials = db.get_all_laser_materials()
                        material = next((m for m in current_materials if m['id'] == material_id), None)
                        if not material:
                            ui.notify('❌ الخامة غير موجودة', color='negative')
                            return

                        with ui.dialog() as dialog, ui.card().classes('p-6 w-96'):
                            ui.label(f"✏️ تعديل {material['name']}").classes('text-lg font-bold mb-4')

                            name_edit = ui.input('اسم الخامة', value=material['name']).classes('mb-2 w-full')
                            side_edit = ui.select(
                                options=['وش', 'ظهر'], 
                                label='نوع الخامة',
                                value=material['material_side']
                            ).classes('mb-2 w-full')
                            purchase_edit = ui.number('سعر الشراء', value=material['purchase_price']).classes('mb-2 w-full')
                            sale_edit = ui.number('سعر البيع', value=material['sale_price']).classes('mb-2 w-full')
                            stock_edit = ui.number('الكمية الحالية', value=material['stock_quantity']).classes('mb-4 w-full')

                            def save_changes():
                                success = db.update_laser_material(
                                    material_id=material['id'],
                                    name=name_edit.value,
                                    material_side=side_edit.value,
                                    purchase_price=purchase_edit.value,
                                    sale_price=sale_edit.value,
                                    stock_quantity=stock_edit.value,
                                )
                                if success:
                                    ui.notify('✅ تم تعديل الخامة بنجاح', color='positive')
                                    dialog.close()
                                    ui.navigate.reload()
                                else:
                                    ui.notify('❌ حصلت مشكلة أثناء التعديل', color='negative')

                            with ui.row().classes('gap-2 w-full'):
                                ui.button('💾 حفظ', on_click=save_changes).classes('bg-blue-500 text-white flex-1')
                                ui.button('❌ إلغاء', on_click=dialog.close).classes('bg-gray-500 text-white flex-1')

                        dialog.open()
                    
                    def delete_material_dialog(material_id):
                        current_materials = db.get_all_laser_materials()
                        material = next((m for m in current_materials if m['id'] == material_id), None)
                        if not material:
                            ui.notify('❌ الخامة غير موجودة', color='negative')
                            return

                        def confirm_delete():
                            success = db.delete_laser_material(material['id'])
                            if success:
                                ui.notify('🗑️ تم حذف الخامة', color='positive')
                                dialog.close()
                                ui.navigate.reload()
                            else:
                                ui.notify('❌ فشل الحذف', color='negative')

                        with ui.dialog() as dialog, ui.card().classes('p-6 w-80'):
                            ui.label(f"⚠️ هل أنت متأكد من حذف {material['name']}؟").classes('text-red-600 mb-4 text-center')
                            ui.label('سيتم حذف جميع المعاملات المرتبطة بهذه الخامة').classes('text-gray-600 mb-4 text-center text-sm')
                            with ui.row().classes('gap-2 w-full'):
                                ui.button('✅ نعم, احذف', on_click=confirm_delete).classes('bg-red-500 text-white flex-1')
                                ui.button('❌ إلغاء', on_click=dialog.close).classes('bg-gray-300 text-black flex-1')

                        dialog.open()
                    
                    table.add_slot('body-cell-actions', '''
                        <q-td :props="props">
                            <q-btn flat round dense @click="$parent.$emit('edit', props.row)" 
                                   icon="edit" color="orange" size="sm">
                                <q-tooltip>تعديل</q-tooltip>
                            </q-btn>
                            <q-btn flat round dense @click="$parent.$emit('delete', props.row)" 
                                   icon="delete" color="red" size="sm">
                                <q-tooltip>حذف</q-tooltip>
                            </q-btn>
                        </q-td>
                    ''')
                    
                    table.on('edit', lambda e: edit_material_dialog(e.args['id']))
                    table.on('delete', lambda e: delete_material_dialog(e.args['id']))
                    
                    
                    low_stock_materials = [m for m in materials if m['stock_quantity'] < 10]
                    if low_stock_materials:
                        with ui.card().classes('p-4 bg-red-50 border-l-4 border-red-500 mt-4'):
                            ui.label('⚠️ تحذير: خامات قاربت على النفاد').classes('text-red-700 font-bold')
                            for material in low_stock_materials:
                                ui.label(f"• {material['name']} ({material['material_side']}): {material['stock_quantity']} قطعة فقط").classes('text-red-600')
                
                else:
                    with ui.card().classes('p-8 text-center'):
                        ui.label('📦 لا توجد خامات مسجلة بعد').classes('text-gray-500 italic text-xl')
                        ui.label('ابدأ بإضافة خامة من تبويب "إضافة خامة"').classes('text-gray-400 mt-2')
            
            
            with ui.tab_panel(add_material_tab):
                ui.label('➕ إضافة خامة جديدة').classes('text-xl font-bold mb-4')
                
                with ui.card().classes('p-6 max-w-xl'):
                    name_input = ui.input('اسم الخامة *').classes('w-full mb-4')
                    name_input.props('outlined dense')
                    
                    side_select = ui.select(
                        options=['وش', 'ظهر'], 
                        label='نوع الخامة *'
                    ).classes('w-full mb-4')
                    side_select.props('outlined dense')
                    
                    with ui.row().classes('gap-4 w-full mb-4'):
                        purchase_input = ui.number('سعر الشراء *', format='%.2f').classes('flex-1')
                        purchase_input.props('outlined dense')
                        
                        sale_input = ui.number('سعر البيع *', format='%.2f').classes('flex-1')
                        sale_input.props('outlined dense')
                    
                    stock_input = ui.number('الكمية الأولية', format='%.0f', value=0).classes('w-full mb-4')
                    stock_input.props('outlined dense')
                    
                    notes_input = ui.textarea('ملاحظات').classes('w-full mb-4')
                    notes_input.props('outlined dense')
                    
                    
                    profit_preview = ui.label('').classes('text-green-600 font-semibold mb-4')
                    
                    def update_profit_preview():
                        if purchase_input.value and sale_input.value:
                            profit = sale_input.value - purchase_input.value
                            profit_percent = (profit / purchase_input.value * 100) if purchase_input.value > 0 else 0
                            color = 'text-green-600' if profit >= 0 else 'text-red-600'
                            profit_preview.text = f"هامش الربح: {profit:.2f} جنيه ({profit_percent:.1f}%)"
                            profit_preview.classes(f'{color} font-semibold mb-4')
                        else:
                            profit_preview.text = ''
                    
                    purchase_input.on('update:model-value', update_profit_preview)
                    sale_input.on('update:model-value', update_profit_preview)
                    
                    def add_material():
                        if not all([name_input.value, side_select.value, purchase_input.value, sale_input.value]):
                            ui.notify('يرجى ملء جميع الحقول المطلوبة (المعلمة بـ *)', color='negative')
                            return
                        
                        success = db.add_laser_material(
                            name=name_input.value.strip(),
                            material_side=side_select.value,
                            purchase_price=purchase_input.value,
                            sale_price=sale_input.value,
                            initial_quantity=stock_input.value or 0,
                            notes=notes_input.value or ''
                        )
                        
                        if success:
                            ui.notify('✅ تم إضافة الخامة بنجاح!', color='positive')
                            
                            name_input.value = ''
                            side_select.value = None
                            purchase_input.value = None
                            sale_input.value = None
                            stock_input.value = 0
                            notes_input.value = ''
                            profit_preview.text = ''
                        else:
                            ui.notify('❌ فشل في إضافة الخامة (ربما الاسم موجود بالفعل)', color='negative')
                    
                    ui.button('➕ إضافة الخامة', on_click=add_material).classes(
                        'w-full bg-blue-500 hover:bg-blue-600 text-white py-3 text-lg font-semibold'
                    )
            
            
            with ui.tab_panel(transaction_tab):
                ui.label('💰 إجراء معاملة').classes('text-xl font-bold mb-4')
                
                materials = db.get_all_laser_materials()
                if not materials:
                    with ui.card().classes('p-8 text-center'):
                        ui.label('📦 لا توجد خامات متاحة').classes('text-gray-500 italic text-xl')
                        ui.label('يجب إضافة خامات أولاً من تبويب "إضافة خامة"').classes('text-gray-400 mt-2')
                else:
                    with ui.card().classes('p-6 max-w-2xl'):
                        
                        material_options = [f"{m['name']} ({m['material_side']}) - متوفر: {m['stock_quantity']}" for m in materials]
                        material_select = ui.select(
                            options=material_options,
                            label='اختر الخامة'
                        ).classes('w-full mb-4')
                        material_select.props('outlined dense')
                        
                        
                        transaction_type = ui.select(
                            options=['شراء خامات', 'بيع', 'استرجاع', 'فاقد/تلف'],
                            label='نوع المعاملة'
                        ).classes('w-full mb-4')
                        transaction_type.props('outlined dense')
                        
                        
                        customer_input = ui.input('اسم العميل').classes('w-full mb-4')
                        customer_input.props('outlined dense')
                        customer_input.bind_visibility_from(transaction_type, 'value', 
                                                          backward=lambda x: x == 'بيع')
                        
                        
                        quantity_input = ui.number('الكمية', format='%.0f', value=1).classes('w-full mb-4')
                        quantity_input.props('outlined dense min=0.1')
                        
                        
                        price_preview = ui.label('').classes('text-blue-600 font-semibold mb-4')
                        
                        
                        transaction_notes = ui.textarea('ملاحظات').classes('w-full mb-4')
                        transaction_notes.props('outlined dense')
                        
                        def update_price_preview():
                            if material_select.value and quantity_input.value and transaction_type.value:
                                
                                material_index = material_options.index(material_select.value) if material_select.value in material_options else -1
                                if material_index >= 0:
                                    selected_material = materials[material_index]
                                    
                                    if transaction_type.value == 'شراء خامات':
                                        price = selected_material['purchase_price'] * quantity_input.value
                                        price_preview.text = f"💰 إجمالي التكلفة: {price:.2f} جنيه"
                                        price_preview.classes('text-blue-600 font-semibold mb-4')
                                    elif transaction_type.value == 'بيع':
                                        price = selected_material['sale_price'] * quantity_input.value
                                        profit = (selected_material['sale_price'] - selected_material['purchase_price']) * quantity_input.value
                                        price_preview.text = f"💰 إجمالي البيع: {price:.2f} جنيه (ربح: {profit:.2f})"
                                        price_preview.classes('text-green-600 font-semibold mb-4')
                                    elif transaction_type.value == 'استرجاع':
                                        price = selected_material['sale_price'] * quantity_input.value
                                        price_preview.text = f"💰 مبلغ الاسترجاع: {price:.2f} جنيه"
                                        price_preview.classes('text-orange-600 font-semibold mb-4')
                                    elif transaction_type.value == 'فاقد/تلف':
                                        price = selected_material['purchase_price'] * quantity_input.value
                                        price_preview.text = f"💸 قيمة الفاقد: {price:.2f} جنيه"
                                        price_preview.classes('text-red-600 font-semibold mb-4')
                                    
                                    
                                    if transaction_type.value in ['بيع', 'فاقد/تلف'] and quantity_input.value > selected_material['stock_quantity']:
                                        price_preview.text += f"\n⚠️ الكمية المطلوبة أكبر من المتوفر ({selected_material['stock_quantity']})"
                                        price_preview.classes('text-red-600 font-semibold mb-4')
                            else:
                                price_preview.text = ''
                        
                        material_select.on('update:model-value', update_price_preview)
                        transaction_type.on('update:model-value', update_price_preview)
                        quantity_input.on('update:model-value', update_price_preview)
                        
                        def process_transaction():
                            if not all([material_select.value, transaction_type.value, quantity_input.value]):
                                ui.notify('يرجى ملء جميع الحقول المطلوبة', color='negative')
                                return
                            
                            if transaction_type.value == 'بيع' and not customer_input.value:
                                ui.notify('يرجى إدخال اسم العميل للبيع', color='negative')
                                return
                            
                            
                            material_index = material_options.index(material_select.value)
                            selected_material = materials[material_index]
                            
                            
                            type_mapping = {
                                'شراء خامات': 'purchase',
                                'بيع': 'sale',
                                'استرجاع': 'return',
                                'فاقد/تلف': 'waste'
                            }
                            
                            success = db.add_laser_transaction(
                                material_id=selected_material['id'],
                                transaction_type=type_mapping[transaction_type.value],
                                quantity=quantity_input.value,
                                customer_name=customer_input.value or '',
                                notes=transaction_notes.value or ''
                            )
                            
                            if success:
                                ui.notify(f'✅ تم تسجيل {transaction_type.value} بنجاح!', color='positive')
                                
                                material_select.value = None
                                transaction_type.value = None
                                customer_input.value = ''
                                quantity_input.value = 1
                                transaction_notes.value = ''
                                price_preview.text = ''
                                
                                ui.navigate.reload()
                            else:
                                ui.notify('❌ فشل في تسجيل المعاملة', color='negative')
                        
                        ui.button('✅ تنفيذ المعاملة', on_click=process_transaction).classes(
                            'w-full bg-green-500 hover:bg-green-600 text-white py-3 text-lg font-semibold'
                        )
            
            
            
            with ui.tab_panel(history_tab): 
                ui.label('📋 سجل المعاملات').classes('text-xl font-bold mb-4')

                
                filter_type = ui.select(
                    options=['جميع المعاملات', 'المشتريات', 'المبيعات', 'المرتجعات', 'الفاقد'],
                    label='تصفية حسب النوع',
                    value='جميع المعاملات'
                ).classes('flex-1 mb-4')

                @ui.refreshable
                def render_transactions():
                    transactions = db.get_laser_transactions()
                    if not transactions:
                        with ui.card().classes('p-8 text-center'):
                            ui.label('📋 لا توجد معاملات مسجلة بعد').classes('text-gray-500 italic text-xl')
                            ui.label('ستظهر المعاملات هنا عند إجرائها').classes('text-gray-400 mt-2')
                        return

                    
                    filter_mapping = {
                        'المشتريات': 'purchase',
                        'المبيعات': 'sale',
                        'المرتجعات': 'return',
                        'الفاقد': 'waste'
                    }

                    with ui.scroll_area().classes('h-96'):
                        for transaction in transactions[:50]:  
                            if (filter_type.value != 'جميع المعاملات' and
                                    transaction['transaction_type'] != filter_mapping.get(filter_type.value)):
                                continue

                            
                            transaction_styles = {
                                'purchase': {'color': 'blue-50 border-blue-200', 'icon': '🛒', 'title': 'شراء'},
                                'sale': {'color': 'green-50 border-green-200', 'icon': '💰', 'title': 'بيع'},
                                'return': {'color': 'yellow-50 border-yellow-200', 'icon': '↩️', 'title': 'استرجاع'},
                                'waste': {'color': 'red-50 border-red-200', 'icon': '🗑️', 'title': 'فاقد'},
                            }
                            style = transaction_styles.get(transaction['transaction_type'], transaction_styles['purchase'])

                            with ui.card().classes(f'p-4 mb-3 {style["color"]} border-l-4'):
                                with ui.row().classes('justify-between items-start w-full'):
                                    with ui.column().classes('flex-1'):
                                        ui.label(f"{style['icon']} {style['title']} - {transaction['material_name']} ({transaction['material_side']})").classes('font-bold text-lg')

                                        details = f"الكمية: {transaction['quantity']:.0f} | سعر الوحدة: {transaction['unit_price']:.2f} جنيه"
                                        if transaction['customer_name']:
                                            details += f" | العميل: {transaction['customer_name']}"
                                        ui.label(details).classes('text-gray-600')

                                        if transaction['notes']:
                                            ui.label(f"📝 {transaction['notes']}").classes('text-sm text-gray-500 italic')

                                    with ui.column().classes('items-end'):
                                        try:
                                            date_obj = datetime.strptime(transaction['date'], "%Y-%m-%d %H:%M:%S")
                                            formatted_date = date_obj.strftime("%d/%m/%Y %H:%M")
                                        except:
                                            formatted_date = transaction['date']

                                        ui.label(formatted_date).classes('text-xs text-gray-500')
                                        ui.label(f"{transaction['total_amount']:.2f} جنيه").classes('text-xl font-bold text-gray-800')

                    
                    with ui.row().classes('gap-4 mt-6 justify-center'):
                        with ui.card().classes('p-4 bg-gray-50'):
                            ui.label('📊 إحصائيات سريعة').classes('font-bold mb-2')
                            ui.label(f"إجمالي المعاملات: {len(transactions)}").classes('text-sm')
                            ui.label(f"معاملات آخر 7 أيام: {analytics['recent_transactions']}").classes('text-sm')

                        if analytics['top_materials']:
                            with ui.card().classes('p-4 bg-gray-50'):
                                ui.label('🔥 أكثر الخامات مبيعاً').classes('font-bold mb-2')
                                for material in analytics['top_materials'][:3]:
                                    ui.label(f"• {material['name']}: {material['sold']} قطعة").classes('text-sm')

                
                ui.button('🔄 تحديث', on_click=render_transactions.refresh).classes('bg-blue-500 text-white')

                
                render_transactions()

                    
                


    shop_ui.create_chat_button()
    shop_ui.create_chat_interface()

import time
import webbrowser
import threading
def open_browser():
    """Wait for the server to start and then open the browser"""
    time.sleep(2)  
    webbrowser.open("http://127.0.0.1:8080/home")

if __name__ in {"__main__", "__mp_main__"}:
    LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "basic": {
            "format": "%(levelname)s | %(name)s | %(message)s"
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "basic",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "uvicorn": {"handlers": ["console"], "level": "INFO"},
        "uvicorn.error": {"handlers": ["console"], "level": "INFO"},
        "uvicorn.access": {"handlers": ["console"], "level": "INFO"},
    },
}
    
    threading.Thread(target=open_browser, daemon=True).start()
    ui.run(
        title="VENOM Shop",
        favicon="🐍",
        dark=False,
        show=True,
        port=8080,
        log_config=LOGGING_CONFIG,
        reload=False
    )
