import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="Terminal - Debugging")

st.title("🛠 System Diagnostic Mode")
st.write("Checking connection to Google AI Servers...")

# بخش دریافت کلید در سایدبار
with st.sidebar:
    st.header("Credentials")
    api_key_input = st.text_input("Paste API Key here:", type="password")

if api_key_input:
    try:
        # پاکسازی فضاهای خالی
        key = api_key_input.strip()
        
        # تلاش برای اتصال
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # یک تست بسیار کوچک برای گرفتن پاسخ از گوگل
        response = model.generate_content("Hello")
        
        if response.text:
            st.success("✅ CONNECTION SUCCESSFUL! Your API Key is working perfectly.")
            st.write("Now you can proceed to use the main tool.")
            st.balloons()

    except Exception as e:
        # نمایش دقیق خطا با جزئیات کامل فنی
        st.error("❌ AN ERROR OCCURRED:")
        st.code(str(e)) # این کد خطا را به ما نشان می‌دهد
        
        # راهنما بر اساس خطاهای رایج
        if "API_KEY_INVALID" in str(e):
            st.info("GUIDE: Your API Key is wrong. Please copy it again from Google AI Studio.")
        elif "User location is not supported" in str(e):
            st.info("GUIDE: Google is blocking this server's location. We need to try a different model.")
        else:
            st.info("GUIDE: Copy the error code above and send it to me.")
else:
    st.warning("Please paste your API Key and press ENTER.")
