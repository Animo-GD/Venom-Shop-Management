from nicegui import ui, app
from src.database.DatabaseHandler import DatabaseHandler
from src.ChatBot.ChatBot import ChatBot,LocalChatBot
from src.GUI.ShopUI import ShopUI
from datetime import datetime, timedelta
import logging
import sys
import webbrowser
import tempfile
import os
import httpx
import json

# --- Initialization ---
db = DatabaseHandler()
shop_ui = ShopUI()

# --- Global State for Date Persistence ---
SETTINGS_FILE = 'app_settings.json'

def load_app_settings():
    """Load app settings including selected dates"""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {
        'start_date': (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
        'end_date': datetime.now().strftime('%Y-%m-%d')
    }

def save_app_settings(settings):
    """Save app settings including selected dates"""
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

# Global settings
app_settings = load_app_settings()

# --- Global Persistent Player ---
with ui.footer().classes('hidden') as footer:
    global_audio_player = ui.audio('')

# --- Global State ---
quran_player_state = {'playing': False}

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

# --- Helper Functions ---
def get_date_range():
    """Returns the start and end date for the analytics query."""
    return app_settings['start_date'] + ' 00:00:00', app_settings['end_date'] + ' 23:59:59'

# --- UI Pages ---

@ui.page('/')
@ui.page('/home')
def home_page():
    """Home page with Quran player as main content"""
    shop_ui.create_header()

    # --- Quran Player Data & Favorites Logic ---
    FAVORITES_FILE = 'favorites.json'
    SURA_NAMES = [
        "الفاتحة", "البقرة", "آل عمران", "النساء", "المائدة", "الأنعام", "الأعراف", "الأنفال", "التوبة", "يونس", "هود",
        "يوسف", "الرعد", "إبراهيم", "الحجر", "النحل", "الإسراء", "الكهف", "مريم", "طه", "الأنبياء", "الحج", "المؤمنون",
        "النور", "الفرقان", "الشعراء", "النمل", "القصص", "العنكبوت", "الروم", "لقمان", "السجدة", "الأحزاب", "سبأ",
        "فاطر", "يس", "الصافات", "ص", "الزمر", "غافر", "فصلت", "الشورى", "الزخرف", "الدخان", "الجاثية", "الأحقاف",
        "محمد", "الفتح", "الحجرات", "ق", "الذاريات", "الطور", "النجم", "القمر", "الرحمن", "الواقعة", "الحديد", "المجادلة",
        "الحشر", "الممتحنة", "الصف", "الجمعة", "المنافقون", "التغابن", "الطلاق", "التحريم", "الملك", "القلم", "الحاقة",
        "المعارج", "نوح", "الجن", "المزمل", "المدثر", "القيامة", "الإنسان", "المرسلات", "النبأ", "النازعات", "عبس",
        "التكوير", "الإنفطار", "المطففين", "الإنشقاق", "البروج", "الطارق", "الأعلى", "الغاشية", "الفجر", "البلد", "الشمس",
        "الليل", "الضحى", "الشرح", "التين", "العلق", "القدر", "البينة", "الزلزلة", "العاديات", "القارعة", "التكاثر", "العصر",
        "الهمزة", "الفيل", "قريش", "الماعون", "الكوثر", "الكافرون", "النصر", "المسد", "الإخلاص", "الفلق", "الناس"
    ]
    sura_options = {i + 1: f"{i + 1}. {name}" for i, name in enumerate(SURA_NAMES)}

    def load_favorites():
        if os.path.exists(FAVORITES_FILE):
            try:
                with open(FAVORITES_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return []
        return []

    def save_favorites(fav_ids):
        with open(FAVORITES_FILE, 'w', encoding='utf-8') as f:
            json.dump(fav_ids, f, ensure_ascii=False, indent=4)

    favorite_reciter_ids = load_favorites()
    all_reciters_data = []

    with ui.column().classes('p-6 max-w-7xl mx-auto items-center w-full'):
        with ui.row(wrap=False).classes('gap-2 items-center mb-6 self-center'):
            title_label = ui.label('🎵 مشغل القرآن الكريم').classes('text-4xl font-bold text-center text-gray-900')
            toggle_button = ui.button(icon='analytics', on_click=lambda: toggle_main_view()).props('flat round dense')

        # --- Quran Player Container (Main view now) ---
        with ui.column().classes('w-full items-center justify-center h-[70vh] gap-4') as quran_container:
            with ui.card().classes('w-full max-w-2xl p-4 sm:p-6 text-center shadow-2xl rounded-2xl bg-white'):
                sura_name_label = ui.label("").classes('text-2xl font-bold text-gray-800 mb-2')
                
                # مشغل HTML مخفي
                audio_player = ui.add_body_html('''
                    <audio id="quranAudio" preload="metadata" style="display: none;">
                        <source type="audio/mpeg">
                        متصفحك لا يدعم تشغيل الصوت
                    </audio>
                    <script>
                        window.quranPlayer = {
                            audio: document.getElementById('quranAudio'),
                            isPlaying: false,
                            
                            play: function() {
                                if (this.audio.src) {
                                    this.audio.play().then(() => {
                                        this.isPlaying = true;
                                        window.dispatchEvent(new CustomEvent('audioPlay'));
                                    }).catch(e => {
                                        console.error('خطأ في التشغيل:', e);
                                        alert('خطأ في تشغيل الصوت. تأكد من الاتصال بالإنترنت.');
                                    });
                                }
                            },
                            
                            pause: function() {
                                this.audio.pause();
                                this.isPlaying = false;
                                window.dispatchEvent(new CustomEvent('audioPause'));
                            },
                            
                            setSource: function(url) {
                                this.audio.src = url;
                                this.audio.load();
                            },
                            
                            togglePlayPause: function() {
                                if (this.isPlaying) {
                                    this.pause();
                                } else {
                                    this.play();
                                }
                            }
                        };
                        
                        // أحداث المشغل
                        window.quranPlayer.audio.addEventListener('play', () => {
                            window.quranPlayer.isPlaying = true;
                            window.dispatchEvent(new CustomEvent('audioPlay'));
                        });
                        
                        window.quranPlayer.audio.addEventListener('pause', () => {
                            window.quranPlayer.isPlaying = false;
                            window.dispatchEvent(new CustomEvent('audioPause'));
                        });
                        
                        window.quranPlayer.audio.addEventListener('ended', () => {
                            window.quranPlayer.isPlaying = false;
                            window.dispatchEvent(new CustomEvent('audioEnded'));
                        });
                    </script>
                ''')
                
                with ui.row().classes('w-full items-center'):
                    reciter_select = ui.select(label="اختر القارئ", options={}).classes('flex-grow')
                    fav_button = ui.button(icon='star_border', on_click=lambda: toggle_favorite()).props('flat round dense color=grey').style('margin-left: -10px;')
                fav_switch = ui.switch('المفضلة فقط').classes('self-start')
                sura_select = ui.select(label="اختر السورة", options=sura_options, value=1).classes('w-full')
                with ui.row().classes('w-full justify-center items-center gap-4 my-4'):
                    prev_button = ui.button(icon='skip_previous').props('round dense size=lg flat')
                    play_pause_button = ui.button(icon='play_arrow').props('round dense size=xl flat')
                    next_button = ui.button(icon='skip_next').props('round dense size=lg flat')

        # Analytics container (Hidden by default now)
        with ui.column().classes('w-full items-center') as analytics_container:
            with ui.row().classes('gap-4 items-center justify-center mb-6'):
                start_date_input = ui.input('من تاريخ').props('type="date"').classes('w-48')
                end_date_input = ui.input('إلى تاريخ').props('type="date"').classes('w-48')
                # Load saved dates
                start_date_input.value = app_settings['start_date']
                end_date_input.value = app_settings['end_date']
            
            with ui.tabs().classes('w-full') as tabs:
                shop_tab = ui.tab('بضاعة المحل')
                laser_tab = ui.tab('ماكينة الليزر')
            
            with ui.tab_panels(tabs, value=shop_tab).classes('w-full mt-4'):
                with ui.tab_panel(shop_tab):
                    shop_analytics_container = ui.column().classes('w-full gap-4')
                with ui.tab_panel(laser_tab):
                    laser_analytics_container = ui.column().classes('w-full gap-4')
            
            def update_analytics():
                # Save selected dates
                app_settings['start_date'] = start_date_input.value
                app_settings['end_date'] = end_date_input.value
                save_app_settings(app_settings)
                
                start = f"{start_date_input.value} 00:00:00"
                end = f"{end_date_input.value} 23:59:59"
                analytics = db.get_analytics_data(start, end)
                
                shop_analytics_container.clear()
                with shop_analytics_container:
                    with ui.row().classes('gap-6 w-full justify-center'):
                        with ui.card().classes('p-6 bg-gradient-to-br from-green-400 to-green-600 text-white flex-1 shadow-lg'):
                            ui.icon('account_balance_wallet', size='2.5rem')
                            ui.label(f"{analytics['shop_revenue']:.2f} جنيه").classes('text-3xl font-bold')
                            ui.label('إجمالي الدخل').classes('text-green-100')
                        with ui.card().classes('p-6 bg-gradient-to-br from-emerald-400 to-emerald-600 text-white flex-1 shadow-lg'):
                            ui.icon('trending_up', size='2.5rem')
                            ui.label(f"{analytics['shop_profit']:.2f} جنيه").classes('text-3xl font-bold')
                            ui.label('صافي الربح').classes('text-emerald-100')
                    
                    with ui.card().classes('p-6 rounded-xl shadow-md w-full mt-4'):
                        ui.label('🔥 المنتجات الأكثر مبيعًا').classes('text-xl font-bold text-gray-900 mb-4 text-center')
                        if analytics['top_shop_products']:
                            for product in analytics['top_shop_products']:
                                with ui.row().classes('justify-between items-center py-2 border-b w-full'):
                                    ui.label(product['name']).classes('font-medium')
                                    ui.label(f"{product['total_sold']} قطعة").classes('text-green-600 font-bold')
                        else:
                            ui.label('لا توجد بيانات مبيعات حالياً').classes('text-gray-500 italic text-center')
                
                laser_analytics_container.clear()
                with laser_analytics_container:
                    with ui.row().classes('gap-6 w-full justify-center'):
                        with ui.card().classes('p-6 bg-gradient-to-br from-blue-400 to-blue-600 text-white flex-1 shadow-lg'):
                            ui.icon('account_balance_wallet', size='2.5rem')
                            ui.label(f"{analytics['laser_revenue']:.2f} جنيه").classes('text-3xl font-bold')
                            ui.label('إجمالي الدخل').classes('text-blue-100')
                        with ui.card().classes('p-6 bg-gradient-to-br from-cyan-400 to-cyan-600 text-white flex-1 shadow-lg'):
                            ui.icon('trending_up', size='2.5rem')
                            ui.label(f"{analytics['laser_profit']:.2f} جنيه").classes('text-3xl font-bold')
                            ui.label('صافي الربح').classes('text-cyan-100')
                    
                    with ui.card().classes('p-6 rounded-xl shadow-md w-full mt-4'):
                        ui.label('🔥 الخامات الأكثر مبيعًا').classes('text-xl font-bold text-gray-900 mb-4 text-center')
                        if analytics['top_laser_materials']:
                            for material in analytics['top_laser_materials']:
                                with ui.row().classes('justify-between items-center py-2 border-b w-full'):
                                    ui.label(material['name']).classes('font-medium')
                                    ui.label(f"{material['total_sold']:.2f} وحدة").classes('text-blue-600 font-bold')
                        else:
                            ui.label('لا توجد بيانات مبيعات حالياً').classes('text-gray-500 italic text-center')
            
            update_analytics()
            start_date_input.on('change', update_analytics)
            end_date_input.on('change', update_analytics)

        # Set initial visibility (Quran visible, analytics hidden)
        analytics_container.set_visibility(False)

    # --- Logic Functions ---
    def toggle_play_pause():
        ui.run_javascript('window.quranPlayer.togglePlayPause()')

    def update_fav_button_icon():
        current_id = reciter_select.value
        if current_id and current_id in favorite_reciter_ids:
            fav_button.props('icon=star color=amber')
        else:
            fav_button.props('icon=star_border color=grey')

    def update_reciter_list(initial_load=False):
        show_favorites = fav_switch.value
        if show_favorites:
            display_data = [r for r in all_reciters_data if r['id'] in favorite_reciter_ids]
        else:
            display_data = all_reciters_data
        
        reciter_options = {reciter['id']: reciter['name'] for reciter in display_data}
        reciter_select.options = reciter_options

        if display_data and (not reciter_select.value or reciter_select.value not in reciter_options):
            reciter_select.value = display_data[0]['id']
        elif not display_data:
            reciter_select.value = None

        reciter_select.update()
        update_fav_button_icon()

        if initial_load and reciter_select.value:
            update_audio_source()

    async def get_reciters():
        nonlocal all_reciters_data
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get('https://mp3quran.net/api/_arabic.json', timeout=15)
                response.raise_for_status()
                data = response.json()
                all_reciters_data = data.get('reciters', [])
                update_reciter_list(initial_load=True)
        except Exception as e:
            ui.notify(f'فشل في تحميل القراء: {e}', color='negative')

    def update_audio_source(play_audio=False):
        update_fav_button_icon()
        
        if not reciter_select.value or not sura_select.value:
            sura_name_label.text = "اختر قارئاً وسورة"
            return
        
        reciter = next((r for r in all_reciters_data if r['id'] == reciter_select.value), None)
        if not reciter:
            return

        sura_number = str(sura_select.value).zfill(3)
        sura_name_label.text = f"سورة {SURA_NAMES[sura_select.value - 1]}"
        audio_url = f"{reciter['Server']}/{sura_number}.mp3"
        
        # تحديث مصدر الصوت
        ui.run_javascript(f'window.quranPlayer.setSource("{audio_url}")')
        
        if play_audio:
            ui.timer(0.5, lambda: ui.run_javascript('window.quranPlayer.play()'), once=True)

    def play_sura(offset: int):
        current_sura = sura_select.value or 1
        new_sura = current_sura + offset
        if 1 <= new_sura <= 114:
            sura_select.value = new_sura
            update_audio_source(play_audio=True)
            
    def toggle_favorite():
        current_id = reciter_select.value
        if not current_id:
            return
        if current_id in favorite_reciter_ids:
            favorite_reciter_ids.remove(current_id)
            ui.notify('تم إزالة من المفضلة', color='info')
        else:
            favorite_reciter_ids.append(current_id)
            ui.notify('تم إضافة للمفضلة', color='positive')
        save_favorites(favorite_reciter_ids)
        update_fav_button_icon()
        if fav_switch.value:
            update_reciter_list()

    def toggle_main_view():
        is_analytics_visible = analytics_container.visible
        analytics_container.set_visibility(not is_analytics_visible)
        quran_container.set_visibility(is_analytics_visible)
        
        if is_analytics_visible:
            # Switching to Quran view
            new_icon = 'analytics'
            title_label.text = '🎵 مشغل القرآن الكريم'
        else:
            # Switching to analytics view
            new_icon = 'music_note'
            title_label.text = '📊 لوحة التحكم'
        
        toggle_button.props(f'icon={new_icon}')
        
    # --- Event Bindings ---
    ui.run_javascript('''
        window.addEventListener('audioPlay', () => {
            document.querySelector('[aria-label="pause"]') || 
            document.querySelectorAll('button').forEach(btn => {
                if (btn.querySelector('i') && btn.querySelector('i').textContent === 'play_arrow') {
                    btn.querySelector('i').textContent = 'pause';
                }
            });
        });
        
        window.addEventListener('audioPause', () => {
            document.querySelectorAll('button').forEach(btn => {
                if (btn.querySelector('i') && btn.querySelector('i').textContent === 'pause') {
                    btn.querySelector('i').textContent = 'play_arrow';
                }
            });
        });
        
        window.addEventListener('audioEnded', () => {
            document.querySelectorAll('button').forEach(btn => {
                if (btn.querySelector('i') && btn.querySelector('i').textContent === 'pause') {
                    btn.querySelector('i').textContent = 'play_arrow';
                }
            });
        });
    ''')

    # ربط أحداث الأزرار
    play_pause_button.on('click', toggle_play_pause)
    prev_button.on('click', lambda: play_sura(-1))
    next_button.on('click', lambda: play_sura(1))
    
    # ربط أحداث القوائم
    reciter_select.on('change', lambda: update_audio_source(play_audio=False))
    sura_select.on('change', lambda: update_audio_source(play_audio=True))
    fav_switch.on('change', lambda: update_reciter_list())
    
    # تحميل البيانات
    ui.timer(1.0, get_reciters, once=True)
    
    shop_ui.create_chat_button()
    shop_ui.create_chat_interface()

@ui.page('/add_items')
def add_items_page():
    shop_ui.create_header()
    with ui.column().classes('p-6 max-w-4xl mx-auto'):
        ui.label('➕ إضافة بضاعة جديدة').classes('text-3xl font-bold text-gray-800 mb-6')
        with ui.tabs().classes('w-full') as tabs:
            shop_tab = ui.tab('منتجات المحل')
            laser_tab = ui.tab('خامات ماكينة الليزر')
        with ui.tab_panels(tabs, value=shop_tab).classes('w-full mt-4'):
            with ui.tab_panel(shop_tab):
                with ui.card().classes('p-8 w-full'):
                    name_input = ui.input('اسم المنتج *').classes('w-full')
                    supplier_input = ui.input('اسم المورد (اختياري)').classes('w-full')
                    with ui.row().classes('w-full gap-4'):
                        price_input = ui.number('سعر الشراء (الجملة) *', format='%.2f').classes('flex-1')
                        stock_input = ui.number('الكمية *', format='%.0f').classes('flex-1')
                    date_input = ui.input('تاريخ الشراء *').props('type="date"').classes('w-full')
                    date_input.value = datetime.now().strftime('%Y-%m-%d')
                    def add_product_action():
                        if not all([name_input.value, price_input.value, stock_input.value, date_input.value]):
                            ui.notify('يرجى ملء جميع الحقول المطلوبة (*)', color='negative')
                            return
                        name = name_input.value.strip()
                        price = float(price_input.value)
                        existing = db.get_product_by_name_and_price(name, price)
                        if existing:
                            with ui.dialog() as dialog, ui.card():
                                ui.label(f'المنتج "{name}" بنفس السعر موجود بالفعل. هل تريد زيادة الكمية؟')
                                with ui.row():
                                    def update_stock():
                                        db.update_product_stock(existing['id'], int(stock_input.value))
                                        ui.notify('تم تحديث الكمية بنجاح', color='positive')
                                        dialog.close()
                                    ui.button('نعم، قم بالتحديث', on_click=update_stock, color='positive')
                                    ui.button('إلغاء', on_click=dialog.close)
                            dialog.open()
                        else:
                            similar_products = [p for p in db.get_all_products() if p['name'] == name]
                            if similar_products:
                                name_to_add = f"{name} ({len(similar_products) + 1})"
                                ui.notify(f'تنبيه: تم تغيير الاسم إلى "{name_to_add}" لوجود منتج بنفس الاسم وسعر مختلف', color='warning')
                            else:
                                name_to_add = name
                            success = db.add_product(
                                name=name_to_add,
                                supplier=supplier_input.value,
                                purchase_date=date_input.value,
                                purchase_price=price,
                                stock=int(stock_input.value)
                            )
                            if success:
                                ui.notify('تم إضافة المنتج بنجاح', color='positive')
                                for i in [name_input, supplier_input, price_input, stock_input]: i.value = None
                            else:
                                ui.notify('فشل في إضافة المنتج', color='negative')
                    ui.button('إضافة المنتج', on_click=add_product_action).classes('w-full mt-4')
            with ui.tab_panel(laser_tab):
                with ui.card().classes('p-8 w-full'):
                    name_input_l = ui.input('اسم الخامة *').classes('w-full')
                    side_select_l = ui.select(options=['وش', 'ظهر'], label='نوع الخامة *').classes('w-full')
                    supplier_input_l = ui.input('اسم المورد (اختياري)').classes('w-full')
                    with ui.row().classes('w-full gap-4'):
                        price_input_l = ui.number('سعر الشراء *', format='%.2f').classes('flex-1')
                        stock_input_l = ui.number('الكمية *', format='%.2f').classes('flex-1')
                    date_input_l = ui.input('تاريخ الشراء *').props('type="date"').classes('w-full')
                    date_input_l.value = datetime.now().strftime('%Y-%m-%d')
                    def add_material_action():
                        if not all([name_input_l.value, side_select_l.value, price_input_l.value, stock_input_l.value, date_input_l.value]):
                            ui.notify('يرجى ملء جميع الحقول المطلوبة (*)', color='negative')
                            return
                        name = name_input_l.value.strip()
                        price = float(price_input_l.value)
                        side = side_select_l.value
                        existing = db.get_laser_material_by_name_side_price(name, side, price)
                        if existing:
                            with ui.dialog() as dialog, ui.card():
                                ui.label(f'الخامة "{name} ({side})" بنفس السعر موجودة. هل تريد زيادة الكمية؟')
                                with ui.row():
                                    def update_stock():
                                        db.update_laser_material_stock(existing['id'], float(stock_input_l.value))
                                        ui.notify('تم تحديث الكمية بنجاح', color='positive')
                                        dialog.close()
                                    ui.button('نعم، قم بالتحديث', on_click=update_stock, color='positive')
                                    ui.button('إلغاء', on_click=dialog.close)
                            dialog.open()
                        else:
                            success = db.add_laser_material(
                                name=name,
                                material_side=side,
                                supplier=supplier_input_l.value,
                                purchase_date=date_input_l.value,
                                purchase_price=price,
                                stock_quantity=float(stock_input_l.value)
                            )
                            if success:
                                ui.notify('تم إضافة الخامة بنجاح', color='positive')
                                for i in [name_input_l, supplier_input_l, price_input_l, stock_input_l, side_select_l]: i.value = None
                            else:
                                ui.notify('فشل في إضافة الخامة', color='negative')
                    ui.button('إضافة الخامة', on_click=add_material_action).classes('w-full mt-4')
    shop_ui.create_chat_button()
    shop_ui.create_chat_interface()

@ui.page('/process_operation')
def process_operation_page():
    shop_ui.create_header()
    with ui.column().classes('p-6 max-w-4xl mx-auto'):
        ui.label('🛒 بيع / عمليات').classes('text-3xl font-bold text-gray-800 mb-6')
        with ui.tabs().classes('w-full') as tabs:
            shop_tab = ui.tab('بضاعة المحل')
            laser_tab = ui.tab('خامات ماكينة الليزر')
        with ui.tab_panels(tabs, value=shop_tab).classes('w-full mt-4'):
            with ui.tab_panel(shop_tab):
                products = db.get_all_products()
                product_options = {p['id']: f"{p['name']} (المتاح: {p['stock']})" for p in products}
                if not product_options:
                    ui.label('لا توجد منتجات متاحة للبيع.').classes('text-center')
                else:
                    item_select = ui.select(options=product_options, label='اختر المنتج *').classes('w-full')
                    operation_type = ui.select(options=['بيع', 'استرجاع', 'تالف'], label='نوع العملية *', value='بيع').classes('w-full')
                    customer_name = ui.input('اسم المشتري *').classes('w-full')
                    customer_phone = ui.input('رقم المشتري (اختياري)').classes('w-full')
                    # إضافة حقل التاريخ
                    operation_date = ui.input('تاريخ العملية *').props('type="date"').classes('w-full')
                    operation_date.value = datetime.now().strftime('%Y-%m-%d')
                    
                    with ui.row().classes('w-full gap-4'):
                        sale_price = ui.number('سعر البيع للقطعة *', format='%.2f').classes('flex-1')
                        quantity = ui.number('الكمية *', value=1).classes('flex-1')
                    def perform_action():
                        if not all ([item_select.value, operation_type.value, customer_name.value, sale_price.value, quantity.value, operation_date.value]):
                            ui.notify('يرجى ملء جميع الحقول المطلوبة (*)', color='negative')
                            return
                        success = db.add_operation_with_date(
                            item_id=item_select.value,
                            item_type='product',
                            operation_type=operation_type.value,
                            customer_name=customer_name.value,
                            customer_phone=customer_phone.value,
                            quantity=float(quantity.value),
                            total_price=float(sale_price.value) * float(quantity.value),
                            operation_date=operation_date.value
                        )
                        if success:
                            ui.notify(f'تمت عملية "{operation_type.value}" بنجاح', color='positive')
                            ui.timer(1.0, lambda: ui.navigate.reload(), once=True)
                        else:
                            ui.notify('فشلت العملية', color='negative')
                    ui.button('تنفيذ', on_click=perform_action).classes('w-full mt-4')
            with ui.tab_panel(laser_tab):
                materials = db.get_all_laser_materials()
                material_options = {m['id']: f"{m['name']} ({m['material_side']}) (المتاح: {m['stock_quantity']})" for m in materials}
                if not material_options:
                    ui.label('لا توجد خامات متاحة.').classes('text-center')
                else:
                    item_select_l = ui.select(options=material_options, label='اختر الخامة *').classes('w-full')
                    operation_type_l = ui.select(options=['بيع', 'استرجاع', 'تالف'], label='نوع العملية *', value='بيع').classes('w-full')
                    customer_name_l = ui.input('اسم المشتري *').classes('w-full')
                    customer_phone_l = ui.input('رقم المشتري (اختياري)').classes('w-full')
                    # إضافة حقل التاريخ
                    operation_date_l = ui.input('تاريخ العملية *').props('type="date"').classes('w-full')
                    operation_date_l.value = datetime.now().strftime('%Y-%m-%d')
                    
                    with ui.row().classes('w-full gap-4'):
                        sale_price_l = ui.number('سعر البيع للوحدة *', format='%.2f').classes('flex-1')
                        quantity_l = ui.number('الكمية *', value=1).classes('flex-1')
                    def perform_action_l():
                        if not all ([item_select_l.value, operation_type_l.value, customer_name_l.value, sale_price_l.value, quantity_l.value, operation_date_l.value]):
                            ui.notify('يرجى ملء جميع الحقول المطلوبة (*)', color='negative')
                            return
                        success = db.add_operation_with_date(
                            item_id=item_select_l.value,
                            item_type='laser',
                            operation_type=operation_type_l.value,
                            customer_name=customer_name_l.value,
                            customer_phone=customer_phone_l.value,
                            quantity=float(quantity_l.value),
                            total_price=float(sale_price_l.value) * float(quantity_l.value),
                            operation_date=operation_date_l.value
                        )
                        if success:
                            ui.notify(f'تمت عملية "{operation_type_l.value}" بنجاح', color='positive')
                            ui.timer(1.0, lambda: ui.navigate.reload(), once=True)
                        else:
                            ui.notify('فشلت العملية', color='negative')
                    ui.button('تنفيذ', on_click=perform_action_l).classes('w-full mt-4')
    shop_ui.create_chat_button()
    shop_ui.create_chat_interface()

@ui.page('/manage_inventory')
def manage_inventory_page():
    shop_ui.create_header()
    with ui.column().classes('p-6 max-w-7xl mx-auto'):
        ui.label('📦 إدارة المخزن').classes('text-3xl font-bold text-gray-800 mb-6')
        with ui.tabs().classes('w-full') as tabs:
            shop_tab = ui.tab('بضاعة المحل')
            laser_tab = ui.tab('خامات ماكينة الليزر')
        with ui.tab_panels(tabs, value=shop_tab).classes('w-full mt-4'):
            with ui.tab_panel(shop_tab):
                @ui.refreshable
                def products_table():
                    products = db.get_all_products()
                    if not products:
                        ui.label('لا توجد منتجات حالياً.').classes('text-center')
                        return
                    for product in products:
                        with ui.card().classes('w-full p-4 mb-2'):
                            with ui.row().classes('w-full justify-between items-center'):
                                with ui.column():
                                    ui.label(product['name']).classes('font-bold text-lg')
                                    ui.label(f"المورد: {product.get('supplier', 'N/A')} | الكمية: {product['stock']}").classes('text-sm text-gray-600')
                                    ui.label(f"شراء: {product['purchase_price']:.2f} | بيع: {product.get('sale_price', 'N/A') or 'لم يحدد'}").classes('text-sm text-gray-600')
                                with ui.row():
                                    ui.button(icon='edit', on_click=lambda p=product: edit_product_dialog(p)).props('flat round')
                                    ui.button(icon='delete', on_click=lambda p=product: delete_item('product', p['id'])).props('flat round color=negative')
                products_table()
            with ui.tab_panel(laser_tab):
                @ui.refreshable
                def materials_table():
                    materials = db.get_all_laser_materials()
                    if not materials:
                        ui.label('لا توجد خامات حالياً.').classes('text-center')
                        return
                    for material in materials:
                        with ui.card().classes('w-full p-4 mb-2'):
                            with ui.row().classes('w-full justify-between items-center'):
                                with ui.column():
                                    ui.label(f"{material['name']} ({material['material_side']})").classes('font-bold text-lg')
                                    ui.label(f"المورد: {material.get('supplier', 'N/A')} | الكمية: {material['stock_quantity']}").classes('text-sm text-gray-600')
                                    ui.label(f"شراء: {material['purchase_price']:.2f} | بيع: {material.get('sale_price', 'N/A') or 'لم يحدد'}").classes('text-sm text-gray-600')
                                with ui.row():
                                    ui.button(icon='edit', on_click=lambda m=material: edit_material_dialog(m)).props('flat round')
                                    ui.button(icon='delete', on_click=lambda m=material: delete_item('laser', m['id'])).props('flat round color=negative')
                materials_table()
    def edit_product_dialog(product):
        with ui.dialog() as dialog, ui.card():
            ui.label(f"تعديل: {product['name']}").classes('text-lg font-bold')
            name = ui.input('الاسم', value=product['name'])
            supplier = ui.input('المورد', value=product.get('supplier'))
            purchase_price = ui.number('سعر الشراء', value=product['purchase_price'])
            sale_price = ui.number('سعر البيع', value=product.get('sale_price'))
            stock = ui.number('الكمية', value=product['stock'])
            notes = ui.textarea('ملاحظات', value=product.get('notes'))
            def save():
                db.update_product(product['id'], name.value, supplier.value, purchase_price.value, sale_price.value, stock.value, notes.value)
                ui.notify('تم الحفظ', color='positive')
                products_table.refresh()
                dialog.close()
            ui.button('حفظ', on_click=save)
        dialog.open()
    def edit_material_dialog(material):
        with ui.dialog() as dialog, ui.card():
            ui.label(f"تعديل: {material['name']}").classes('text-lg font-bold')
            name = ui.input('الاسم', value=material['name'])
            side = ui.select(['وش', 'ظهر'], label='النوع', value=material['material_side'])
            supplier = ui.input('المورد', value=material.get('supplier'))
            purchase_price = ui.number('سعر الشراء', value=material['purchase_price'])
            sale_price = ui.number('سعر البيع', value=material.get('sale_price'))
            stock_quantity = ui.number('الكمية', value=material['stock_quantity'])
            notes = ui.textarea('ملاحظات', value=material.get('notes'))
            def save():
                db.update_laser_material(material['id'], name.value, side.value, supplier.value, purchase_price.value, sale_price.value, stock_quantity.value, notes.value)
                ui.notify('تم الحفظ', color='positive')
                materials_table.refresh()
                dialog.close()
            ui.button('حفظ', on_click=save)
        dialog.open()
    def delete_item(item_type, item_id):
        with ui.dialog() as dialog, ui.card():
            ui.label('هل أنت متأكد من الحذف؟')
            with ui.row():
                def confirmed_delete():
                    if item_type == 'product':
                        db.delete_product(item_id)
                        products_table.refresh()
                    else:
                        db.delete_laser_material(item_id)
                        materials_table.refresh()
                    ui.notify('تم الحذف', color='positive')
                    dialog.close()
                ui.button('نعم', on_click=confirmed_delete, color='negative')
                ui.button('لا', on_click=dialog.close)
        dialog.open()
    shop_ui.create_chat_button()
    shop_ui.create_chat_interface()

@ui.page('/history')
def history_page():
    shop_ui.create_header()
    with ui.column().classes('p-6 max-w-7xl mx-auto'):
        ui.label('📜 السجل').classes('text-3xl font-bold text-gray-800 mb-6')
        operations = db.get_all_operations()
        columns = [
            {'name': 'date', 'label': 'التاريخ', 'field': 'date', 'sortable': True, 'align': 'center'},
            {'name': 'type', 'label': 'نوع العملية', 'field': 'operation_type', 'align': 'center'},
            {'name': 'item', 'label': 'اسم المنتج/الخامة', 'field': 'item_name', 'align': 'left'},
            {'name': 'quantity', 'label': 'الكمية', 'field': 'quantity', 'align': 'center'},
            {'name': 'price', 'label': 'التكلفة', 'field': 'total_price', 'align': 'center'},
            {'name': 'customer', 'label': 'صاحب العملية', 'field': 'customer_name', 'align': 'left'},
        ]
        table = ui.table(columns=columns, rows=operations, row_key='id').classes('w-full shadow-lg')
        with table.add_slot('top-right'):
            with ui.input(placeholder='ابحث...').props('dense clearable').bind_value(table, 'filter') as filter_input:
                with filter_input.add_slot('append'):
                    ui.icon('search')
    shop_ui.create_chat_button()
    shop_ui.create_chat_interface()

import time
import webbrowser
import threading
def open_browser():
    """Wait for the server to start and then open the browser"""
    time.sleep(2)  
    webbrowser.open("http://127.0.0.1:8080/home")

# --- Main App Execution ---
if __name__ in {"__main__", "__mp_main__"}:
    LOGGING_CONFIG = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"basic": {"format": "%(levelname)s | %(name)s | %(message)s"}},
        "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "basic", "stream": "ext://sys.stdout"}},
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
        show=False,
        port=8080,
        log_config=LOGGING_CONFIG,
        reload=False
    )