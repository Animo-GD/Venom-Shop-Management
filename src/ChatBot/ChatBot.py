from dotenv import load_dotenv
import asyncio
from typing import Optional
import aiohttp
import json
import os
from src.database.DatabaseHandler import DatabaseHandler
db = DatabaseHandler()
class ChatBot:
    def __init__(self, api_key: str = None, model: Optional[str] = None):
        load_dotenv()
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            print("⚠️ Warning: No OpenRouter API key found. Chat will not work without API key.")
            self.api_key = None
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = model or os.getenv("MODEL_NAME") or "meta-llama/llama-3.2-3b-instruct:free"

    async def get_response(self, message: str, context: str = "") -> str:
        """Get response from OpenRouter API with proper error handling"""
        
        # Check if API key is available
        if not self.api_key:
            return "❌ لم يتم تكوين مفتاح API. يرجى إضافة OPENROUTER_API_KEY في ملف .env"
        
        # Validate input
        if not message or not message.strip():
            return "❌ يرجى كتابة رسالة صحيحة"

        try:
            # Prepare the payload
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are Osama, a helpful assistant for a mobile accessories shop called VENOM. "
                            "Respond in simple Arabic. When answering questions about inventory or sales, "
                            "Use Egyptian currency only"
                            "use the provided context data. If information is not in the context, say: "
                            "'لا أملك بيانات كافية عن هذا الموضوع'"
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"سياق من قاعدة البيانات:\n{context}\n\nالسؤال: {message}",
                    },
                ],
                "max_tokens": 500,
                "temperature": 0.7,
                "stream": False
            }

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:8080",
                "X-Title": "Venom Shop Assistant",
            }

            # Use timeout for the request
            timeout = aiohttp.ClientTimeout(total=30)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                try:
                    async with session.post(self.base_url, headers=headers, json=payload) as resp:
                        response_text = await resp.text()
                        
                        if resp.status == 200:
                            try:
                                data = await resp.json()
                                if "choices" in data and len(data["choices"]) > 0:
                                    content = data["choices"][0]["message"]["content"]
                                    return content.strip() if content else "❌ الرد فارغ من النموذج"
                                else:
                                    return f"❌ شكل الرد غير صحيح: {data}"
                            except json.JSONDecodeError as e:
                                return f"❌ خطأ في قراءة JSON: {str(e)}"
                        
                        elif resp.status == 401:
                            return "❌ مفتاح API غير صحيح أو منتهي الصلاحية"
                        elif resp.status == 429:
                            return "❌ تم تجاوز حد الاستخدام، جرب مرة أخرى لاحقاً"
                        elif resp.status == 400:
                            return "❌ خطأ في البيانات المرسلة للـ API"
                        else:
                            return f"❌ خطأ API {resp.status}: {response_text[:200]}"
                            
                except aiohttp.ClientError as e:
                    return f"❌ خطأ في الاتصال: {str(e)}"
                    
        except asyncio.TimeoutError:
            return "❌ انتهت مهلة الاتصال، جرب مرة أخرى"
        except Exception as e:
            return f"❌ خطأ غير متوقع: {str(e)}"

    def test_connection(self) -> bool:
        """Test if the API key and connection are working (synchronous version)"""
        if not self.api_key:
            return False
        
        import requests
        try:
            response = requests.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": "test"}],
                    "max_tokens": 10
                },
                timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False
        

class LocalChatBot:
    def __init__(self):
        self.responses = {
            'سلام': 'وعليكم السلام! أهلاً بك في محل VENOM 😊',
            'مرحبا': 'أهلاً وسهلاً! كيف يمكنني مساعدتك اليوم؟',
            'مبيعات': 'إجمالي المبيعات موجود في الرئيسية، أو اسألني عن منتج معين',
            'مخزون': 'يمكنك مشاهدة المخزون في صفحة إدارة المنتجات',
            'ربح': 'صافي الربح معروض في لوحة التحكم الرئيسية',
            'مساعدة': 'يمكنني مساعدتك في:\n- معلومات عن المبيعات\n- حالة المخزون\n- البحث عن المنتجات\n- حساب الأرباح'
        }
    def _search_laser_materials(self, search_term: str, materials_data: list) -> list:
        """Search for laser materials containing the search term"""
        if not materials_data:
            return []
        
        results = []
        for material in materials_data:
            if (search_term.lower() in material.get('name', '').lower() or 
                search_term.lower() in material.get('material_side', '').lower()):
                results.append(material)
        return results

    def _search_laser_transactions(self, search_term: str, transactions_data: list) -> list:
        """Search for laser transactions"""
        if not transactions_data:
            return []
        
        results = []
        for transaction in transactions_data:
            if (search_term.lower() in transaction.get('material_name', '').lower() or 
                search_term.lower() in transaction.get('customer_name', '').lower() or
                search_term in transaction.get('date', '')):
                results.append(transaction)
        return results
    async def get_response(self, message: str, context: str = "") -> str:
        """Get response using local logic and context data"""
        message_lower = message.lower().strip()
        
        analytics_data = {}
        laser_analytics = {}
        full_orders = []
        full_products = []
        laser_materials = []
        laser_transactions = []
        
        if context:
            try:
                data = json.loads(context)
                analytics_data = data.get('main_shop', {})
                laser_analytics = data.get('laser', {})
                
                # Get full data from database
                full_orders = db.get_all_orders()
                full_products = db.get_all_products()
                laser_materials = db.get_all_laser_materials()
                laser_transactions = db.get_laser_transactions()
                
            except:
                pass

        response = ""

        # Laser-specific queries
        if any(word in message_lower for word in ['ليزر', 'laser', 'خامات', 'خامة']):
            # Laser analytics query
            if any(word in message_lower for word in ['ربح', 'مكسب', 'خسارة', 'analytics']):
                if laser_analytics:
                    response = f'''⚡ إحصائيات مكينة الليزر:
    💰 إجمالي المشتريات: {laser_analytics.get("total_purchases", 0):.2f} جنيه
    💵 صافي المبيعات: {laser_analytics.get("net_sales", 0):.2f} جنيه  
    📈 المكسب/الخسارة: {laser_analytics.get("net_profit", 0):.2f} جنيه
    🗑️ قيمة الفاقد: {laser_analytics.get("total_waste", 0):.2f} جنيه
    📦 عدد أنواع الخامات: {laser_analytics.get("materials_count", 0)}'''
                else:
                    response = "مالقيتش بيانات عن مكينة الليزر"

            # Laser materials stock query
            elif any(word in message_lower for word in ['مخزون', 'متوفر', 'stock']):
                if laser_materials:
                    response = "📦 خامات الليزر المتوفرة:\n\n"
                    for material in laser_materials[:10]:
                        stock_status = "🔴" if material['stock_quantity'] < 10 else "🟢"
                        response += f"{stock_status} {material['name']} ({material['material_side']})\n"
                        response += f"   الكمية: {material['stock_quantity']:.0f} | البيع: {material['sale_price']:.2f} جنيه\n\n"
                else:
                    response = "مفيش خامات ليزر مسجلة حالياً"

            # Specific material search
            elif len([w for w in message_lower.split() if len(w) > 2]) > 1:
                search_terms = [w for w in message_lower.split() if len(w) > 2 and w not in ['ليزر', 'خامة', 'خامات', 'laser']]
                found_materials = []
                for term in search_terms:
                    found_materials.extend(self._search_laser_materials(term, laser_materials))
                
                if found_materials:
                    response = "🔍 الخامات اللي لقيتها:\n\n"
                    for material in found_materials[:5]:
                        profit = material['sale_price'] - material['purchase_price']
                        response += f"📦 {material['name']} ({material['material_side']})\n"
                        response += f"   المتوفر: {material['stock_quantity']:.0f}\n"
                        response += f"   الشراء: {material['purchase_price']:.2f} | البيع: {material['sale_price']:.2f}\n"
                        response += f"   الربح: {profit:.2f} جنيه للقطعة\n\n"
                else:
                    response = f"مالقيتش خامات تحتوي على: {', '.join(search_terms)}"

        # Laser transaction date queries
        elif any(word in message_lower for word in ['متى', 'امتى', 'تاريخ']) and any(word in message_lower for word in ['ليزر', 'خامة', 'خامات']):
            search_terms = []
            words = message_lower.split()
            skip_words = ['متى', 'امتى', 'تاريخ', 'ليزر', 'خامة', 'خامات', 'اشترى', 'باع']
            
            for word in words:
                if len(word) > 2 and word not in skip_words:
                    search_terms.append(word)
            
            if search_terms and laser_transactions:
                found_transactions = []
                for term in search_terms:
                    found_transactions.extend(self._search_laser_transactions(term, laser_transactions))
                
                if found_transactions:
                    response = "🕐 معاملات الليزر اللي لقيتها:\n\n"
                    for transaction in found_transactions[:5]:
                        transaction_type_ar = {
                            'purchase': 'شراء',
                            'sale': 'بيع', 
                            'return': 'استرجاع',
                            'waste': 'فاقد'
                        }.get(transaction['transaction_type'], transaction['transaction_type'])
                        
                        formatted_date = self._format_date_arabic(transaction['date'])
                        response += f"⚡ {transaction_type_ar} - {transaction['material_name']} ({transaction['material_side']})\n"
                        response += f"   الكمية: {transaction['quantity']:.0f} | المبلغ: {transaction['total_amount']:.2f} جنيه\n"
                        if transaction['customer_name']:
                            response += f"   العميل: {transaction['customer_name']}\n"
                        response += f"   📅 {formatted_date}\n\n"
                else:
                    response = f"مالقيتش معاملات ليزر تحتوي على: {', '.join(search_terms)}"

        # Check for low stock laser materials
        elif any(word in message_lower for word in ['قارب', 'نفد', 'خلص', 'قليل']) and any(word in message_lower for word in ['ليزر', 'خامة']):
            if laser_materials:
                low_stock = [m for m in laser_materials if m['stock_quantity'] < 10]
                if low_stock:
                    response = "⚠️ خامات الليزر اللي قاربت تخلص:\n\n"
                    for material in low_stock:
                        response += f"🔴 {material['name']} ({material['material_side']})\n"
                        response += f"   متبقي: {material['stock_quantity']:.0f} قطعة فقط\n\n"
                else:
                    response = "الحمد لله، كل خامات الليزر متوفرة بكمية كافية 👍"
            else:
                response = "مفيش خامات ليزر مسجلة للفحص"

        # If no laser-specific response, fall back to original logic
        if not response:
            
            if any(word in message_lower for word in ['سلام', 'السلام', 'مرحبا', 'أهلا']):
                response = 'أهلاً وسهلاً! 😊 اسألني عن المحل الرئيسي أو مكينة الليزر'

            elif any(word in message_lower for word in ['مبيعات', 'دخل', 'إيراد']) and 'ليزر' not in message_lower:
                if 'total_revenue' in analytics_data:
                    response = f'إجمالي مبيعات المحل: {analytics_data["total_revenue"]} جنيه 💰'
                else:
                    response = 'يمكنك مشاهدة المبيعات في لوحة التحكم الرئيسية'

            elif any(word in message_lower for word in ['ربح', 'أرباح']) and 'ليزر' not in message_lower:
                if 'total_profit' in analytics_data:
                    response = f'ربح المحل الرئيسي: {analytics_data["total_profit"]} جنيه 📈'
                else:
                    response = 'الأرباح معروضة في لوحة التحكم الرئيسية'

            elif any(word in message_lower for word in ['مخزون', 'بضاعة', 'منتجات']) and 'ليزر' not in message_lower:
                response = f"منتجات المحل: {analytics_data.get('products_count', '؟')} منتج\n"
                if 'low_stock_products' in analytics_data and analytics_data['low_stock_products']:
                    response += f"⚠️ منتجات قاربت تخلص: {', '.join(analytics_data['low_stock_products'][:3])}"

            elif any(word in message_lower for word in ['مساعدة', 'help']):
                response = '''يمكنني مساعدتك في:
    🔸 معلومات المحل الرئيسي (مبيعات، مخزون، أرباح)
    ⚡ معلومات مكينة الليزر (خامات، مبيعات، مكاسب)
    🔍 البحث بالتاريخ والعملاء
    📊 إحصائيات مفصلة

    جرب تقول:
    • "ربح الليزر"
    • "خامات الليزر المتوفرة" 
    • "متى اشترى أحمد من الليزر؟"'''

            elif any(word in message_lower for word in ['شكرا', 'تسلم', 'ممتاز']):
                response = 'العفو! 😊 أي خدمة تانية للمحل أو الليزر؟'

            else:
                # Enhanced default response
                main_info = ""
                laser_info = ""
                
                if analytics_data:
                    main_info = f'''💰 المحل الرئيسي: {analytics_data.get("total_revenue", "؟")} جنيه مبيعات
    📦 المنتجات: {analytics_data.get("products_count", "؟")} منتج'''
                
                if laser_analytics:
                    laser_info = f'''⚡ مكينة الليزر: {laser_analytics.get("net_profit", "؟")} جنيه ربح
    🔥 الخامات: {laser_analytics.get("materials_count", "؟")} نوع'''
                
                if main_info or laser_info:
                    response = f'''معلومات سريعة:
    {main_info}
    {laser_info}

    جرب تسأل عن:
    🔹 "ربح الليزر" أو "خامات متوفرة"
    🔹 "متى العميل فلان اشترى؟"  
    🔹 "آخر معاملات الليزر"'''
                else:
                    response = '''أسف، مش فاهم سؤالك. جرب تسأل عن:
    🔹 المبيعات والأرباح (المحل أو الليزر)
    🔹 المخزون والمنتجات
    🔹 "متى العميل فلان اشترى؟"
    🔹 "خامات الليزر المتوفرة"'''

        # Add to memory
        self._add_to_memory(message, response)
        
        return response
