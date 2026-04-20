import streamlit as st
import pandas as pd
import networkx as nx
import plotly.express as px
import plotly.graph_objects as go

st.title("Network Analysis")
st.write(
    "This page examines Citi Bike station connectivity in the Jersey City–Hoboken area "
    "using trip data from January to March 2025."
)

# -----------------------------
# Load data
# -----------------------------
od = pd.read_csv("data/od_edges.csv")

# -----------------------------
# 1. Top Station-to-Station Flows
# -----------------------------
st.subheader("Top 10 Station-to-Station Flows")

od["route"] = od["start_station_name"] + " → " + od["end_station_name"]
top_pairs = od.sort_values("trip_count", ascending=False).head(10)

fig_pairs = px.bar(
    top_pairs.sort_values("trip_count", ascending=True),
    x="trip_count",
    y="route",
    orientation="h",
    title="Top 10 Station-to-Station Flows",
    labels={"trip_count": "Number of Trips", "route": "Station Pair"}
)

st.plotly_chart(fig_pairs, use_container_width=True)

st.write(
    "The strongest flows are concentrated among a small number of specific station-to-station routes. "
    "Major corridors appear around Grove St PATH, Liberty Light Rail, and McGinley Square, "
    "suggesting repeated movement between important mobility nodes."
)

# -----------------------------
# 2. Top 10 Most Connected Stations
# -----------------------------
st.subheader("Top 10 Most Connected Stations")

outflow = (
    od.groupby(["start_station_name", "start_station_id"], as_index=False)
    .agg(outflow=("trip_count", "sum"))
    .rename(columns={
        "start_station_name": "station_name",
        "start_station_id": "station_id"
    })
)

inflow = (
    od.groupby(["end_station_name", "end_station_id"], as_index=False)
    .agg(inflow=("trip_count", "sum"))
    .rename(columns={
        "end_station_name": "station_name",
        "end_station_id": "station_id"
    })
)

station_flow = pd.merge(outflow, inflow, on=["station_name", "station_id"], how="outer").fillna(0)
station_flow["total_flow"] = station_flow["outflow"] + station_flow["inflow"]

top_stations = station_flow.sort_values("total_flow", ascending=False).head(10)

fig_stations = px.bar(
    top_stations.sort_values("total_flow", ascending=True),
    x="total_flow",
    y="station_name",
    orientation="h",
    title="Top 10 Most Connected Stations",
    labels={"total_flow": "Total Flow (In + Out)", "station_name": "Station"}
)

st.plotly_chart(fig_stations, use_container_width=True)

st.write(
    "Grove St PATH and Hoboken Terminal - River St & Hudson Pl appear to be the most active stations "
    "when total incoming and outgoing trips are combined. This suggests that Citi Bike activity is concentrated "
    "around a small number of hub locations."
)

# -----------------------------
# 3. Filtered Network Map
# -----------------------------
st.subheader("Filtered Citi Bike Station Network on Map")

top_edges = od.sort_values("trip_count", ascending=False).head(50).copy()

fig_map = go.Figure()
max_weight = top_edges["trip_count"].max()

for _, row in top_edges.iterrows():
    line_width = 1 + 8 * (row["trip_count"] / max_weight)

    fig_map.add_trace(
        go.Scattermapbox(
            mode="lines",
            lon=[row["start_lng"], row["end_lng"]],
            lat=[row["start_lat"], row["end_lat"]],
            line=dict(width=line_width, color="rgba(200, 50, 50, 0.45)"),
            hoverinfo="text",
            text=f"{row['start_station_name']} → {row['end_station_name']}<br>Trips: {row['trip_count']}",
            showlegend=False
        )
    )

node_sizes_dict = station_flow.set_index("station_name")["total_flow"].to_dict()
max_node_flow = station_flow["total_flow"].max()

nodes_in_top = set(top_edges["start_station_name"]).union(set(top_edges["end_station_name"]))

node_lon = []
node_lat = []
node_text = []
node_size = []

for station in nodes_in_top:
    start_match = top_edges[top_edges["start_station_name"] == station]
    end_match = top_edges[top_edges["end_station_name"] == station]

    if not start_match.empty:
        lon = start_match.iloc[0]["start_lng"]
        lat = start_match.iloc[0]["start_lat"]
    else:
        lon = end_match.iloc[0]["end_lng"]
        lat = end_match.iloc[0]["end_lat"]

    node_lon.append(lon)
    node_lat.append(lat)
    node_text.append(f"{station}<br>Total flow: {node_sizes_dict.get(station, 0):,.0f}")
    node_size.append(8 + 22 * (node_sizes_dict.get(station, 0) / max_node_flow))

fig_map.add_trace(
    go.Scattermapbox(
        mode="markers",
        lon=node_lon,
        lat=node_lat,
        marker=dict(size=node_size, color="royalblue", opacity=0.8),
        text=node_text,
        hoverinfo="text",
        showlegend=False
    )
)

fig_map.update_layout(
    title="Filtered Citi Bike Station Network on Map (Top 50 Flows)",
    mapbox=dict(
        style="carto-positron",
        center=dict(lat=40.725, lon=-74.045),
        zoom=12.2
    ),
    margin=dict(l=20, r=20, t=60, b=20),
    height=750
)

st.plotly_chart(fig_map, use_container_width=True)

st.write(
    "The filtered network map shows that the strongest Citi Bike connections are concentrated around a few key hubs, "
    "especially Grove St PATH, Hoboken Terminal, and nearby transit-linked stations. "
    "This suggests strong local clustering rather than a uniform network."
)

# -----------------------------
# 4. Top 10 Stations by Weighted Degree
# -----------------------------
st.subheader("Top 10 Stations by Weighted Degree")

G = nx.DiGraph()

for _, row in od.iterrows():
    G.add_edge(
        row["start_station_name"],
        row["end_station_name"],
        weight=row["trip_count"]
    )

weighted_degree_dict = dict(G.degree(weight="weight"))
degree_dict = dict(G.degree())

metrics_df = pd.DataFrame({
    "station_name": list(weighted_degree_dict.keys()),
    "weighted_degree": list(weighted_degree_dict.values()),
    "degree": [degree_dict[s] for s in weighted_degree_dict.keys()]
})

metrics_df = metrics_df.sort_values("weighted_degree", ascending=False)
top_weighted = metrics_df.head(10).copy()
top_weighted["station_label"] = top_weighted["station_name"]

fig_weighted = px.bar(
    top_weighted.sort_values("weighted_degree", ascending=True),
    x="weighted_degree",
    y="station_label",
    orientation="h",
    title="Top 10 Stations by Weighted Degree",
    labels={
        "weighted_degree": "Weighted Degree",
        "station_label": "Station"
    },
    height=650
)

fig_weighted.update_traces(marker_color="#636EFA")
fig_weighted.update_layout(
    template="plotly",
    margin=dict(l=260, r=40, t=60, b=40)
)
fig_weighted.update_yaxes(title=None)

st.plotly_chart(fig_weighted, use_container_width=True)

st.write(
    "Weighted degree shows which stations are the most central from a network perspective. "
    "Grove St PATH and Hoboken Terminal again rank highest, meaning they are not only busy "
    "but also strongly connected within the wider system."
)
