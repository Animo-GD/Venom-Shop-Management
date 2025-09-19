from dotenv import load_dotenv
import asyncio
from typing import Optional, Dict, List
import aiohttp
import json
import os
from datetime import datetime
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

    def _search_products(self, search_term: str, products_data: List[Dict]) -> List[Dict]:
        """Search for products containing the search term in name, supplier, or notes"""
        if not products_data:
            return []
        
        results = []
        search_lower = search_term.lower()
        for product in products_data:
            if (search_lower in product.get('name', '').lower() or
                search_lower in product.get('supplier_name', '').lower() or
                search_lower in product.get('notes', '').lower()):
                results.append(product)
        return results

    def _search_materials(self, search_term: str, materials_data: List[Dict]) -> List[Dict]:
        """Search for laser materials containing the search term in name, supplier, or notes"""
        if not materials_data:
            return []
        
        results = []
        search_lower = search_term.lower()
        for material in materials_data:
            if (search_lower in material.get('name', '').lower() or 
                search_lower in material.get('material_side', '').lower() or
                search_lower in material.get('supplier_name', '').lower() or
                search_lower in material.get('notes', '').lower()):
                results.append(material)
        return results

    def _search_orders(self, search_term: str, orders_data: List[Dict]) -> List[Dict]:
        """Search for orders containing the search term"""
        if not orders_data:
            return []
        
        results = []
        search_lower = search_term.lower()
        for order in orders_data:
            if (search_lower in order.get('name', '').lower() or 
                search_lower in order.get('product_name', '').lower() or
                search_lower in order.get('date', '') or
                search_lower in order.get('customer_phone', '')):
                results.append(order)
        return results
        
    def _search_laser_transactions(self, search_term: str, transactions_data: List[Dict]) -> List[Dict]:
        """Search for laser transactions"""
        if not transactions_data:
            return []
        
        results = []
        search_lower = search_term.lower()
        for transaction in transactions_data:
            if (search_lower in transaction.get('material_name', '').lower() or 
                search_lower in transaction.get('customer_name', '').lower() or
                search_lower in transaction.get('customer_phone', '').lower() or
                search_lower in transaction.get('notes', '').lower() or
                search_lower in transaction.get('date', '')):
                results.append(transaction)
        return results
    
    def _format_date_arabic(self, date_str: str) -> str:
        """Formats a date string to a more readable Arabic format (without time)"""
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            return date_obj.strftime("%d/%m/%Y")
        except:
            return date_str

    def _add_to_memory(self, user_message: str, bot_response: str):
        """Adds message and response to memory (placeholder)"""
        pass
    
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
        
        # General queries
        if 'مساعدة' in message_lower or 'help' in message_lower:
            response = '''يمكنني مساعدتك في:
    🔸 معلومات المحل الرئيسي (مبيعات، مخزون، أرباح)
    ⚡ معلومات مكينة الليزر (خامات، مبيعات، مكاسب)
    🔍 البحث بالتواريخ، الموردين، العملاء، أو الملاحظات
    📊 إحصائيات مفصلة

    جرب تسأل عن:
    • "ربح المحل"
    • "متى اشترى احمد؟"
    • "مين مورد سامسونج؟"
    • "ابحث عن خامة ملاحظتها فيها تلف"'''
        elif any(word in message_lower for word in ['سلام', 'السلام', 'مرحبا', 'أهلا']):
            response = 'أهلاً وسهلاً! 😊 اسألني عن المحل الرئيسي أو مكينة الليزر'
        elif any(word in message_lower for word in ['شكرا', 'تسلم', 'ممتاز']):
            response = 'العفو! 😊 أي خدمة تانية للمحل أو الليزر؟'

        # Main Shop-specific queries
        if not response and any(word in message_lower for word in ['محل', 'بضاعة', 'منتجات']) and not any(word in message_lower for word in ['ليزر', 'laser', 'خامات']):
            
            # Main shop analytics query
            if any(word in message_lower for word in ['ربح', 'مكسب', 'خسارة', 'مبيعات', 'دخل', 'إيراد']):
                if analytics_data:
                    response = f'''📊 إحصائيات المحل الرئيسي:
    💰 إجمالي الدخل: {analytics_data.get("total_revenue", 0):.2f} جنيه
    📈 صافي الربح: {analytics_data.get("total_profit", 0):.2f} جنيه
    📉 إجمالي الخسارة (بيع تحت التكلفة): {analytics_data.get("total_loss", 0):.2f} جنيه
    🛒 عدد الطلبات: {analytics_data.get("total_orders", 0)}
    📦 عدد المنتجات: {analytics_data.get("products_count", 0)}'''
                else:
                    response = "مالقيتش بيانات عن المحل الرئيسي"
            
            # Specific product search
            elif len([w for w in message_lower.split() if len(w) > 2]) > 1:
                search_terms = [w for w in message_lower.split() if len(w) > 2 and w not in ['محل', 'بضاعة', 'منتجات']]
                found_products = []
                for term in search_terms:
                    found_products.extend(self._search_products(term, full_products))
                
                if found_products:
                    response = "🔍 المنتجات اللي لقيتها:\n\n"
                    for product in found_products[:5]:
                        profit = product['sale_price'] - product['purchase_price']
                        response += f"📦 {product['name']}\n"
                        response += f"   المورد: {product['supplier_name'] or 'لا يوجد'}\n"
                        response += f"   المتوفر: {product['stock']:.0f}\n"
                        response += f"   الشراء: {product['purchase_price']:.2f} | البيع: {product['sale_price']:.2f}\n"
                        response += f"   الربح: {profit:.2f} جنيه للقطعة\n"
                        if product['notes']:
                            response += f"   ملاحظات: {product['notes']}\n"
                        response += "\n"
                else:
                    response = f"مالقيتش منتجات تحتوي على: {', '.join(search_terms)}"

        # Laser-specific queries
        if not response and any(word in message_lower for word in ['ليزر', 'laser', 'خامات', 'خامة']):
            
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
                    response = "مالقيتش بيانات كافية عن مكينة الليزر"
            
            # Specific material search
            elif len([w for w in message_lower.split() if len(w) > 2]) > 1:
                search_terms = [w for w in message_lower.split() if len(w) > 2 and w not in ['ليزر', 'خامة', 'خامات', 'laser', 'وش', 'ظهر']]
                found_materials = []
                for term in search_terms:
                    found_materials.extend(self._search_materials(term, laser_materials))
                
                if found_materials:
                    response = "🔍 الخامات اللي لقيتها:\n\n"
                    for material in found_materials[:5]:
                        profit = material['sale_price'] - material['purchase_price']
                        response += f"📦 {material['name']} ({material['material_side']})\n"
                        response += f"   المورد: {material['supplier_name'] or 'لا يوجد'}\n"
                        response += f"   المتوفر: {material['stock_quantity']:.0f}\n"
                        response += f"   الشراء: {material['purchase_price']:.2f} | البيع: {material['sale_price']:.2f}\n"
                        response += f"   الربح: {profit:.2f} جنيه للقطعة\n"
                        if material['notes']:
                             response += f"   ملاحظات: {material['notes']}\n"
                        response += "\n"
                else:
                    response = f"مالقيتش خامات تحتوي على: {', '.join(search_terms)}"

        # Order/Transaction queries (main shop & laser)
        if not response and any(word in message_lower for word in ['متى', 'امتى', 'تاريخ', 'عميل', 'اشترى', 'باع', 'سجل', 'ملاحظات']):
            
            if 'ليزر' in message_lower or 'خامة' in message_lower:
                search_terms = [w for w in message_lower.split() if len(w) > 2 and w not in ['متى', 'امتى', 'تاريخ', 'عميل', 'اشترى', 'باع', 'سجل', 'ملاحظات', 'ليزر', 'خامة', 'خامات', 'laser']]
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
                            'waste': 'تالف'
                        }.get(transaction['transaction_type'], transaction['transaction_type'])
                        
                        formatted_date = self._format_date_arabic(transaction['date'])
                        response += f"⚡ {transaction_type_ar} - {transaction['material_name']} ({transaction['material_side']})\n"
                        response += f"   الكمية: {transaction['quantity']:.0f} | المبلغ: {transaction['total_amount']:.2f} جنيه\n"
                        if transaction['customer_name']:
                            response += f"   العميل: {transaction['customer_name'] or 'لا يوجد'}\n"
                        if transaction['notes']:
                            response += f"   ملاحظات: {transaction['notes']}\n"
                        response += f"   📅 {formatted_date}\n\n"
                else:
                    response = f"مالقيتش معاملات ليزر تحتوي على: {', '.join(search_terms)}"
            
            elif 'محل' in message_lower or 'بضاعة' in message_lower:
                search_terms = [w for w in message_lower.split() if len(w) > 2 and w not in ['متى', 'امتى', 'تاريخ', 'عميل', 'اشترى', 'باع', 'سجل', 'ملاحظات', 'محل', 'بضاعة']]
                found_orders = []
                for term in search_terms:
                    found_orders.extend(self._search_orders(term, full_orders))
                
                if found_orders:
                    response = "📋 الأوردرات اللي لقيتها:\n\n"
                    for order in found_orders[:5]:
                        formatted_date = self._format_date_arabic(order['date'])
                        response += f"🛒 بيع - {order['product_name']}\n"
                        response += f"   العميل: {order['name'] or 'لا يوجد'}\n"
                        response += f"   الكمية: {order['quantity']} | المبلغ: {order['total_price']:.2f} جنيه\n"
                        response += f"   📅 {formatted_date}\n\n"
                else:
                    response = f"مالقيتش أوردرات تحتوي على: {', '.join(search_terms)}"

        # If no specific response, fall back to enhanced default response
        if not response:
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