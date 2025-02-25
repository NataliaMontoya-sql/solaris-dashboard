import pandas as pd
import streamlit as st
import plotly.express as px
import folium
import seaborn as sns
import matplotlib.pyplot as plt
from streamlit_folium import st_folium
from branca.element import Template, MacroElement

# Configuración de la página
st.set_page_config(page_title="Proyecto Solaris", page_icon="", layout="wide")
st.title("Proyecto Solaris")
st.sidebar.title("Opciones de Navegación")

st.sidebar.subheader("Carga de archivos CSV")
# Subida de archivos
uploaded_datos = st.sidebar.file_uploader("Sube datos unificados", type=["csv"])
uploaded_humedad = st.sidebar.file_uploader("Sube datos de humedad", type=["csv"])
uploaded_precipitacion = st.sidebar.file_uploader("Sube datos de precipitación", type=["csv"])
uploaded_temperatura = st.sidebar.file_uploader("Sube datos de temperatura", type=["csv"])

# Función para cargar datos a partir de un file uploader
@st.cache_data
def cargar_csv(file) -> pd.DataFrame:
    return pd.read_csv(file)

# Variables de datos
if uploaded_datos is not None:
    df_all = cargar_csv(uploaded_datos)
    # Crear columna Fecha
    df_all['Fecha'] = pd.to_datetime(
        df_all.astype(str).loc[:, ["YEAR", "MO", "DY"]].agg('-'.join, axis=1)
    )
else:
    st.warning("Sube el archivo de datos unificados")
    df_all = None

if uploaded_humedad is not None:
    df_humedad = cargar_csv(uploaded_humedad)
    df_humedad = df_humedad.rename(columns={"RH2M": "humedad"})
else:
    st.warning("Sube el archivo de datos de humedad")
    df_humedad = None

if uploaded_precipitacion is not None:
    df_precipitacion = cargar_csv(uploaded_precipitacion)
    df_precipitacion = df_precipitacion.rename(columns={"PRECTOTCORR": "precipitacion"})
else:
    st.warning("Sube el archivo de datos de precipitación")
    df_precipitacion = None

if uploaded_temperatura is not None:
    df_temperatura = cargar_csv(uploaded_temperatura)
    df_temperatura = df_temperatura.rename(columns={"T2M": "temperatura"})
else:
    st.warning("Sube el archivo de datos de temperatura")
    df_temperatura = None

# Función para crear mapas climáticos con leyenda personalizada
def crear_mapa_clima(df, columna, titulo):
    max_row = df.loc[df[columna].idxmax()]
    map_center = [max_row["LAT"], max_row["LON"]]
    mapa = folium.Map(location=map_center, zoom_start=6)
    
    q75 = df[columna].quantile(0.75)
    q50 = df[columna].quantile(0.50)
    
    for _, row in df.iterrows():
        valor = row[columna]
        if valor > q75:
            color = 'green'
        elif valor > q50:
            color = 'orange'
        else:
            color = 'red'
        
        folium.CircleMarker(
            location=[row['LAT'], row['LON']],
            radius=valor * 0.1,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.6,
            popup=f"{titulo}: {valor:.2f}"
        ).add_to(mapa)
    
    # Crear leyenda personalizada
    legend_html = f"""
    {{% macro html(this, kwargs) %}}
    <div style="
        position: fixed; 
        bottom: 50px; left: 50px; width: 220px; height: 120px; 
        border:2px solid grey; z-index:9999; font-size:14px;
        background-color: white;
        opacity: 0.8;
        padding: 10px;
        ">
        <b>Leyenda</b><br>
        <i class="fa fa-circle" style="color:red"></i>&nbsp; Valor <= {q50:.2f}<br>
        <i class="fa fa-circle" style="color:orange"></i>&nbsp; {q50:.2f} < Valor <= {q75:.2f}<br>
        <i class="fa fa-circle" style="color:green"></i>&nbsp; Valor > {q75:.2f}
    </div>
    {{% endmacro %}}
    """

    macro = MacroElement()
    macro._template = Template(legend_html)
    mapa.get_root().add_child(macro)
    
    return mapa

# Verificar que df_all esté cargado para continuar
if df_all is not None:
    # Agregar columna de Region
    def get_region(lat, lon):
        if lat > 8:
            return "Caribe"
        elif lat < 2:
            return "Sur"
        elif lon < -75:
            return "Pacífico"
        return "Andina"
    
    df_all['Region'] = df_all.apply(lambda x: get_region(x['LAT'], x['LON']), axis=1)

# Menú de navegación
menu = st.sidebar.selectbox("Selecciona una opción:", [
    "Inicio", "Datos", "Visualización", "Mapa Principal", 
    "Mapas Climáticos", "Análisis Detallado", "Matriz de Correlación", "Percentiles"
])

if menu == "Datos":
    st.subheader("Datos Disponibles")
    if df_all is not None:
        st.dataframe(df_all)
    else:
        st.error("Sube el archivo de datos unificados.")

elif menu == "Inicio":
    st.subheader("¡Bienvenidos!")
    st.text("Dashboard para analizar zonas de potencial para parques solares en Colombia.")
    st.markdown("""
    El dashboard se divide en:
    - Tabla de datos
    - Mapas interactivos
    - Análisis visual y estadístico
    """)

elif menu == "Visualización":
    st.subheader("Visualización de Datos Climáticos")
    if df_all is not None:
        año = st.sidebar.selectbox("Selecciona el año", df_all["YEAR"].unique())
        df_filtrado = df_all[df_all["YEAR"] == año]
        st.write(f"Mostrando datos para el año: {año}")
        
        fechas = st.sidebar.date_input(
            "Selecciona el rango de fechas:",
            [df_filtrado["Fecha"].min(), df_filtrado["Fecha"].max()]
        )
        if len(fechas) == 2:
            fecha_inicio, fecha_fin = fechas
            df_filtrado = df_filtrado[(df_filtrado["Fecha"] >= pd.to_datetime(fecha_inicio)) & 
                                      (df_filtrado["Fecha"] <= pd.to_datetime(fecha_fin))]
        
        latitudes_disponibles = df_filtrado["LAT"].unique()
        longitudes_disponibles = df_filtrado["LON"].unique()
        
        lat = st.sidebar.selectbox("Selecciona la latitud", latitudes_disponibles)
        lon = st.sidebar.selectbox("Selecciona la longitud", longitudes_disponibles)
        
        df_filtrado_lat_lon = df_filtrado[(df_filtrado["LAT"] == lat) & (df_filtrado["LON"] == lon)]
        
        mapa = folium.Map(location=[lat, lon], zoom_start=10)
        folium.Marker(
            location=[lat, lon],
            popup=f"Lat: {lat}, Lon: {lon}",
            icon=folium.Icon(color="blue")
        ).add_to(mapa)
        st.subheader("Mapa de Ubicación")
        st_folium(mapa, width=700, height=400)
        
        fig = px.line(
            df_filtrado_lat_lon,
            x="Fecha",
            y=["ALLSKY_KT"],
            title=f"Irradiancia en Lat: {lat} y Lon: {lon} para el año {año}",
            template="plotly_dark"
        )
        st.plotly_chart(fig)
    else:
        st.error("Sube el archivo de datos unificados.")

elif menu == "Mapa Principal":
    st.subheader("Mapa de Calor de Radiación Solar")
    if df_all is not None:
        zoom_level = st.sidebar.slider("Nivel de Zoom", 4, 15, 6)
        fig = px.scatter_mapbox(
            df_all, lat='LAT', lon='LON', color='ALLSKY_KT',
            size=[3]*len(df_all), hover_name='LAT', zoom=zoom_level,
            color_continuous_scale='plasma', mapbox_style='open-street-map',
            center={'lat': 4.5709, 'lon': -74.2973},
            opacity=0.15
        )
        fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=700)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("Sube el archivo de datos unificados.")

elif menu == "Análisis Detallado":
    st.subheader("Análisis de Datos Climáticos")
    if df_all is not None:
        region_avg = df_all.groupby('Region')['ALLSKY_SFC_SW_DWN'].mean()
        st.bar_chart(region_avg)
        df_all['Viabilidad'] = (df_all['ALLSKY_SFC_SW_DWN'] * 0.6 + df_all['ALLSKY_KT'] * 0.4)
        top3 = df_all.nlargest(3, 'Viabilidad')
        for i, (_, row) in enumerate(top3.iterrows()):
            st.metric(f"Ubicación {i+1}", f"{row['Viabilidad']:.2f} pts", f"Lat: {row['LAT']:.4f} Lon: {row['LON']:.4f}")
    else:
        st.error("Sube el archivo de datos unificados.")

elif menu == "Matriz de Correlación":
    st.subheader("Matriz de Correlación")
    uploaded_corr = st.sidebar.file_uploader("Sube datos para la correlación", type=["csv"])
    if uploaded_corr is not None:
        df_corr = cargar_csv(uploaded_corr)
        df_corr = df_corr.rename(columns={
            "RH2M": "Humedad relativa", 
            "T2M": "Temperatura", 
            "ALLSKY_SFC_SW_DWN": "Índice de claridad", 
            "ALLSKY_KT": "Irradiancia solar", 
            "PRECTOTCORR": "Precipitacion"
        })
        columnas_deseadas = ["Irradiancia solar", "Índice de claridad", "Temperatura", "Humedad relativa", "Precipitacion"]
        df_seleccionado = df_corr[columnas_deseadas]
        matriz_correlacion = df_seleccionado.corr()
        plt.figure(figsize=(10,8))
        sns.heatmap(matriz_correlacion, annot=True, cmap='coolwarm', fmt=".2f", linewidths=.5)
        plt.title('Matriz de Correlación')
        st.pyplot(plt)
    else:
        st.error("Sube el archivo de datos para la correlación.")

elif menu == "Mapas Climáticos":
    st.subheader("Mapas de Humedad, Precipitación y Temperatura")
    tipo_mapa = st.selectbox("Selecciona el tipo de mapa:", ["Humedad", "Precipitación", "Temperatura"])
    mapa = None
    if tipo_mapa == "Humedad":
        if df_humedad is not None:
            mapa = crear_mapa_clima(df_humedad, "humedad", "Humedad")
        else:
            st.error("Sube el archivo de datos de humedad.")
    elif tipo_mapa == "Precipitación":
        if df_precipitacion is not None:
            mapa = crear_mapa_clima(df_precipitacion, "precipitacion", "Precipitación")
        else:
            st.error("Sube el archivo de datos de precipitación.")
    elif tipo_mapa == "Temperatura":
        if df_temperatura is not None:
            mapa = crear_mapa_clima(df_temperatura, "temperatura", "Temperatura")
        else:
            st.error("Sube el archivo de datos de temperatura.")
    if mapa:
        st_folium(mapa, width=700, height=400)

elif menu == "Percentiles":
    st.subheader("Mapa con percentiles de irradiación")
    if df_all is not None:
        percentil_seleccionado = st.sidebar.radio("Selecciona el percentil:", ["75", "50"], index=0)
        percentil_valor = 0.75 if percentil_seleccionado == "75" else 0.50

        df_promedio = df_all.groupby(['LAT', 'LON'])['ALLSKY_KT'].mean().reset_index()
        percentil = df_all['ALLSKY_KT'].quantile(percentil_valor)
        df_puntos_altos = df_promedio[df_promedio['ALLSKY_KT'] > percentil]
        df_puntos_bajos = df_promedio[df_promedio['ALLSKY_KT'] <= percentil]

        mapa = folium.Map(location=[df_promedio['LAT'].mean(), df_promedio['LON'].mean()], zoom_start=6)

        for _, row in df_puntos_altos.iterrows():
            folium.CircleMarker(
                location=[row['LAT'], row['LON']],
                radius=8,
                color="red",
                fill=True,
                fill_color="red",
                fill_opacity=0.6,
                popup=f"Lat: {row['LAT']} - Lon: {row['LON']}<br>Promedio ALLSKY_KT: {row['ALLSKY_KT']:.2f}"
            ).add_to(mapa)

        for _, row in df_puntos_bajos.iterrows():
            radius = 4 + (row['ALLSKY_KT'] / df_promedio['ALLSKY_KT'].max()) * 10
            folium.CircleMarker(
                location=[row['LAT'], row['LON']],
                radius=radius,
                color="blue",
                fill=True,
                fill_color="blue",
                fill_opacity=0.6,
                popup=f"Lat: {row['LAT']} - Lon: {row['LON']}<br>Promedio ALLSKY_KT: {row['ALLSKY_KT']:.2f}"
            ).add_to(mapa)

        st.subheader(f"Mapa de puntos mayores y menores al Percentil {percentil_seleccionado}")
        st_folium(mapa, width=700, height=400)
    else:
        st.error("Sube el archivo de datos unificados.")

if __name__ == "__main__":
    st.sidebar.info("Ejecuta este script con: streamlit run nombre_del_script.py")
