import streamlit as st
import pandas as pd
from st_files_connection import FilesConnection
from streamlit_extras.metric_cards import style_metric_cards
from streamlit_extras.metric_cards import style_metric_cards
from PIL import Image
from streamlit_echarts import st_echarts
import numpy as np
import pydeck as pdk
import matplotlib.pyplot as plt
import folium
from streamlit_folium import folium_static
from google.oauth2 import service_account
from google.cloud import bigquery

st.markdown('<style>.css-1544g2n {padding-top: 1rem; padding-right: 1rem; padding-bottom: 1.5rem; padding-left: 1rem} </style>', unsafe_allow_html=True)
st.markdown('<style>.css-1y4p8pa {max-width: 100rem; padding-top: 0rem} </style>', unsafe_allow_html=True)
st.markdown('<style>.css-1nm2qww {position: fixed} </style>', unsafe_allow_html=True)


def connectionBigQuery():
    credentials = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])
    client = bigquery.Client(credentials=credentials)
    # Perform query.
    # Uses st.cache_data to only rerun when the query changes or after 10 min.
    @st.cache_data(ttl=600)
    def run_query(query):
        query_job = client.query(query)
        rows_raw = query_job.result()
        rows = [dict(row) for row in rows_raw]
        return rows
    rows = run_query('SELECT * FROM `maximal-record-388109.orders_data.orders_table` LIMIT 10')

    df = pd.DataFrame(rows)
    # Display the DataFrame using st.dataframe()
    #st.dataframe(df)
    

# Function to read data from Google Cloud Storage
def connectionGCS():

    conn = st.experimental_connection('gcs', type=FilesConnection)
    df = conn.read(f"gs://orders_and_shipments/merged_orders_and_shipments.csv", input_format='csv')
    return df

# Function to read data from a local CSV file
def connectionCSV():
    df = pd.read_csv(r"data/merged_orders_and_shipments.csv")
    return df

# Function to prepare data for stacked line chart
def prepare_data(df):
    series_data = []
    for market in df['Customer Market'].unique():
        # Seçilen markete göre filtrele
        data_filtered = df[df['Customer Market'] == market]
        # 'Order Month' ve 'Order ID' sütunlarına göre grupla ve say
        data_grouped = data_filtered.groupby(' Order Month ')['Order ID '].count().reset_index()
        # Series data oluştur
        series_data.append({
            "name": market,
            "type": "line",
            "stack": market,
            "data": data_grouped['Order ID '].tolist(),
        })
    return series_data

if __name__ == "__main__":

    df = connectionGCS()

    st.header("SUPPLY CHAIN ANALYTICS")

    #st.divider()

    col1, col2, col3, col4 = st.columns(4)
    
    # Sidebar
    image = Image.open('images/icon.jpg')
    st.sidebar.image(image)
    
    ####
    total_orders = df['Order ID '].nunique()
    most_ordered_category = df['Product Category'].value_counts().idxmax()
    most_ordered_country = df['Customer Country'].value_counts().idxmax()
    average_delivery_time = df[' Shipment Days - Scheduled '].mean()
    average_delivery_time = round(average_delivery_time, 2)
    # Metric
    col1.metric(label="Total Orders", value=total_orders)
    col2.metric(label="Most Ordered Category", value=most_ordered_category)
    col3.metric(label="Country with Most Orders", value=most_ordered_country)
    col4.metric(label="Average Delivery Time (days)", value=average_delivery_time)
    style_metric_cards()


    #Stacked Line Chart
    st.markdown('**Number of Orders Over Time by Market**')
    series_data = prepare_data(df)
    months_ordered = sorted(df[' Order Month '].unique().tolist())  # Ay listesini sırala
    
    options = {
        "title": {"text": ""},
        "tooltip": {"trigger": "axis"},
        "legend": {"data": df['Customer Market'].unique().tolist()},
        "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True},
        "toolbox": {"feature": {"saveAsImage": {}}},
        "xAxis": {
            "type": "category",
            "boundaryGap": False,
            "data": months_ordered,  # Sıralanmış ay listesini kullan
            "axisLabel": {"interval": 1},  # Her altıncı etiketi göster
        },
        "yAxis": {"type": "value"},
        "series": series_data
    }
    st_echarts(options=options, height="400px")

    col1, col2= st.columns(2)

    # Map
    # Group data by country and sum up the quantities
    grouped = df.groupby('Customer Country')['Order Quantity'].sum().reset_index()

    # Add latitude and longitude to the grouped data
    grouped['lat'] = df.groupby('Customer Country')['Latitude'].mean().values
    grouped['lon'] = df.groupby('Customer Country')['Longitude'].mean().values

    with col1:
        # Create a map
        m = folium.Map(location=[0, 0], zoom_start=2)

        # Add circles to the map
        for i in range(0,len(grouped)):
            folium.Circle(
                location=[grouped.iloc[i]['lat'], grouped.iloc[i]['lon']],
                popup=str(grouped.iloc[i]['Order Quantity']),
                radius=float(grouped.iloc[i]['Order Quantity']*100),
                color='purple',
                fill=True,
                weight = 2
                
            ).add_to(m)

        # Display the map
        folium_static(m)

    #BarChart
    with col2:
        sales_by_year = df.groupby(' Order Year ')['Order Quantity'].sum().reset_index()

        # Sorting the data for better visualization
        sales_by_year = sales_by_year.sort_values(' Order Year ')
        options = {
        "xAxis": {
            "type": "category",
            "data": sales_by_year[' Order Year '].astype(str).tolist(),
        },
        "yAxis": {"type": "value"},
        "series": [{"data": sales_by_year['Order Quantity'].tolist(), "type": "bar"}],
            }
        st_echarts(options=options, height="500px")
