# python -m streamlit run bookstore.py
from toml import TomlDecodeError
import toml
import csv
import streamlit as st
from datetime import datetime
import pandas as pd
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import copy
import os
import json


# 讀取設定檔
with open('./config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)


# 初始化身份驗證
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
    config['preauthorized']
)
# global login
# login = 0

# 初始化使用者資訊
if "user_info" not in st.session_state:
    st.session_state.user_info = {
        "name": None,
        "shopping_cart": [],
        "order_history": []
    }

# 用戶訂單歷史檔案路徑
orders_path = "./orders/"

# 確保訂單目錄存在
if not os.path.exists(orders_path):
    os.makedirs(orders_path)

# 加載用戶訂單歷史


def load_user_order_history(username):
    order_history_file = f"{orders_path}/{username}.csv"
    if os.path.exists(order_history_file):
        return pd.read_csv(order_history_file)
    return pd.DataFrame(columns=["title", "quantity"])

# 保存用戶訂單歷史


def save_user_order_history(username, current_orders):
    order_history_file = f"{orders_path}/{username}.csv"
    if os.path.exists(order_history_file):
        # 如果檔案已存在，則讀取並附加新訂單
        existing_orders = pd.read_csv(order_history_file)
        updated_orders = pd.concat(
            [existing_orders, pd.DataFrame(current_orders)], ignore_index=True)
    else:
        # 如果檔案不存在，則創建新的 DataFrame
        updated_orders = pd.DataFrame(current_orders)

    # 保存更新後的訂單歷史
    updated_orders.to_csv(order_history_file, index=False)


def login_page():
    # 在登入頁面以對話框的形式顯示用戶消息
    page = st.sidebar.radio("選擇頁面", ["我要訂購", "購物車", "歷史訂單", "留言板"])
    if page == "我要訂購":
        view_products()
    elif page == "歷史訂單":
        order_history()
    elif page == "購物車":
        shopping_cart_page()
    elif page == "留言板":
        message_board()


csv_file_path = 'book.csv'

# 讀取CSV檔案，將資料存入DataFrame

books = pd.read_csv(csv_file_path)


# 初始化 session_state
if "shopping_cart" not in st.session_state:
    st.session_state.shopping_cart = []

# 定義各頁面

# 首頁


def home():
    st.title("麗文書店")
    st.write("歡迎光臨麗文書店線上購！")


# 商品總覽
def view_products():
    st.title("圖書總覽")
    # 製作圖書類型篩選器
    option = st.selectbox('選擇圖書類型',
                          ["All", "Fiction", "Classics", "Dystopian", "Coming-of-age", "Fantasy"])
    if option == "All":
        books_1 = books
    else:
        books_1 = books[books["genre"] == option].reset_index(drop=True)

    # 製作打字搜尋框，讓篩選跟打字搜尋同時運作
    search = st.text_input("請輸入要找的書名，或ISBN")
    if len(search) > 0:
        books_1 = books_1[books_1[['title', 'isbn']].apply(lambda row: any(
            search.lower() in str(cell).lower() for cell in row), axis=1)].reset_index(drop=True)

    if len(books_1) == 0:
        st.write("找無此圖書，請重新輸入")
    else:
        for i in range(len(books_1)):
            st.write(f"## {books_1.at[i, 'title']}")
            st.image(books_1.at[i, "image"],
                     caption=books_1.at[i, "title"], width=300)
            st.write(f"**作者:** {books_1.at[i, 'author']}")
            st.write(f"**類型:** {books_1.at[i, 'genre']}")
            st.write(f"**金額:** {books_1.at[i, 'price']}")
            st.write(f"**ISBN:** {str(books_1.at[i, 'isbn'])}")
            st.write(f"**優惠價:** {books_1.at[i, 'discount_price']}")
            quantity = st.number_input(
                f"購買數量 {i}", min_value=1, value=1, key=f"quantity_{i}")

            # 依照數量計算優惠後價格
            if quantity < 5:
                price = int(books_1.at[i, 'price'])
            elif 5 <= quantity < 10:
                price = round(int(books_1.at[i, 'price'])*0.92, 0)
            elif quantity >= 10:
                price = round(int(books_1.at[i, 'price'])*0.9, 0)

            if st.button(f"購買 {books_1.at[i, 'title']}", key=f"buy_button_{i}"):
                if "shopping_cart" not in st.session_state:
                    st.session_state.shopping_cart = []
                st.session_state.shopping_cart.append({
                    "書名": books_1.at[i, "title"],
                    "ISBN": str(books_1.at[i, "isbn"]),
                    "購買數量": quantity,
                    # Total price calculation
                    "總金額": int(price * int(quantity))
                })
                st.write(f"已將 {quantity} 本 {books_1.at[i, 'title']} 加入購物車")

            st.write("---")


# 顯示訂單
def display_order():
    st.title("訂單明細")

    # 顯示購物車中的商品
    for item in st.session_state.shopping_cart:
        st.write(f"{item['購買數量']} 本 {item['書名']}")

    # 顯示其他訂單相關資訊，例如總金額、訂單時間等

    total_expense = sum(item["總金額"]
                        for item in st.session_state.shopping_cart)
    st.write(f"總金額: {total_expense}")

    order_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.write(f"訂單時間: {order_time}")

# 購物車頁面


def shopping_cart_page():
    st.title("購物車")

    if not st.session_state.shopping_cart:
        st.write("購物車是空的，快去選購您喜歡的書籍吧！")
    else:
        # Create a Pandas DataFrame from the shopping cart data
        df = pd.DataFrame(st.session_state.shopping_cart)

        # Display the DataFrame as a table
        st.table(df)

        pay = st.button('結帳')

        if pay:
            st.session_state.show_payment = True
        if 'show_payment' in st.session_state and st.session_state.show_payment:
            Payment_page()


# 結帳頁面
def Payment_page():
    st.title("結帳")
    with st.form(key="購物清單") as form:
        購買詳情 = display_order()
        付款方式 = st.selectbox('請選擇付款方式', ['信用卡', 'Line Pay'])
        優惠碼 = st.text_input('優惠代碼')
        寄送方式 = st.selectbox('請選擇領取門市', ['中山大學門市', '其他門市'])
        其他門市 = st.text_input("若選其他門市，請輸入其他門市名稱")

        submitted = st.form_submit_button("確認付款")

    if submitted:
        order_history_df = pd.DataFrame(st.session_state.shopping_cart)
        # 保存用戶訂單歷史
        save_user_order_history(
            st.session_state.user_info["name"], order_history_df)
        st.session_state.shopping_cart = []
        st.image(
            'https://cdn.icon-icons.com/icons2/894/PNG/512/Tick_Mark_icon-icons.com_69146.png')
        st.write("送出成功，訂單處理中!")
        st.write("繼續購物請到「我要訂購」頁面!")

# 留言頁


def message_board():
    # 初始化 session_state
    if "past_messages" not in st.session_state:
        st.session_state.past_messages = []

    # 在應用程式中以對話框的形式顯示用戶消息
    with st.chat_message("user"):
        st.write("歡迎來到留言板！")

    # 接收用戶輸入
    prompt = st.text_input("在這裡輸入您的留言")

    # 如果用戶有輸入，則將留言加入 session_state 中
    if prompt:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.session_state.past_messages.append(
            {"user": "user", "message": f"{timestamp} - {prompt}"})

    # 留言板中顯示過去的留言
    with st.expander("過去的留言"):
        # 顯示每條留言
        for message in st.session_state.past_messages:
            with st.chat_message(message["user"]):
                st.write(message["message"])


# 訂單歷史頁面
def order_history():
    st.title("訂單歷史")
    # 將訂單資料轉換為 DataFrame
    df = load_user_order_history(st.session_state.user_info["name"])

    # 顯示表格
    st.table(df)


def main():

    st.title("麗文書店")
    st.write("歡迎光臨麗文書店線上購！")
    st.image(
        "https://www.liwen.com.tw/upload/banner/202008141140134nu2n.jpg")
    st.session_state.login = False

    # 登入
    name, authentication_status, username = authenticator.login(
        'Login', 'main')
    st.session_state.login = authentication_status
    if authentication_status:
        with st.sidebar:
            st.write(f'歡迎! *{name}* ')
        authenticator.logout('Logout', 'sidebar')
        st.session_state.user_info["name"] = name
        # 加載用戶訂單歷史
        st.session_state.user_info["order_history"] = load_user_order_history(
            username)
        login_page()
    elif authentication_status == False:
        st.error('Username/password is incorrect')
    elif authentication_status == None:
        st.warning('Please enter your username and password')


if __name__ == "__main__":
    main()
