from flask import Flask, render_template, request, jsonify
import pandas as pd
import os

app = Flask(__name__)

def load_all_data():
    datasets = [
        "data/cleaned_luzon_dataset.csv",
        "data/cleaned_visayas_dataset.csv",
        "data/cleaned_mindanao_dataset.csv"
    ]
    df_list = []
    for path in datasets:
        if os.path.exists(path):
            df = pd.read_csv(path)
            df_list.append(df)
    return pd.concat(df_list, ignore_index=True)

def load_data_by_island(island_group=None):
    datasets = {
        "Luzon": "data/cleaned_luzon_dataset.csv",
        "Visayas": "data/cleaned_visayas_dataset.csv",
        "Mindanao": "data/cleaned_mindanao_dataset.csv"
    }
    if island_group and island_group in datasets:
        path = datasets[island_group]
        if os.path.exists(path):
            return pd.read_csv(path)
        return pd.DataFrame()
    return load_all_data()

@app.route("/api/island-groups")
def get_island_groups():
    return jsonify(["All Island Groups", "Luzon", "Visayas", "Mindanao"])

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/data")
def get_chart_data():
    region = request.args.get("region", None)
    year = request.args.get("year", None)
    
    df = load_all_data()
    
    if region:
        df = df[df["Region"] == region]
    if year:
        df = df[df["Year"] == int(year)]
    
    df["Cases"] = pd.to_numeric(df["Cases"], errors="coerce")
    df["Deaths"] = pd.to_numeric(df["Deaths"], errors="coerce")
    df["Date"] = pd.to_datetime(df["Date"], format="%d/%m/%Y")
    df = df.dropna(subset=["Cases", "Deaths", "Date"])
    
    df = df.sort_values("Date")
    grouped = df.groupby("Date").agg({"Cases": "sum", "Deaths": "sum"}).reset_index()
    grouped["Cases"] = grouped["Cases"].clip(upper=1000000)
    grouped["Deaths"] = grouped["Deaths"].clip(upper=1000000)
    
    result = {
        "dates": grouped["Date"].dt.strftime("%Y-%m-%d").tolist(),
        "cases": grouped["Cases"].astype(int).tolist(),
        "deaths": grouped["Deaths"].astype(int).tolist()
    }
    return jsonify(result)

@app.route("/api/years")
def get_years():
    df = load_all_data()
    years = sorted(df["Year"].unique().tolist()) if not df.empty else []
    return jsonify(years)
    
@app.route("/api/location-data")
def get_location_data():
    region = request.args.get("region", None)
    year = request.args.get("year", None)  # Added year parameter
    
    df = load_all_data()
    
    if region:
        df = df[df["Region"] == region]
    if year:  # Apply year filter if provided
        df = df[df["Year"] == int(year)]
    
    df["Cases"] = pd.to_numeric(df["Cases"], errors="coerce")
    df["Deaths"] = pd.to_numeric(df["Deaths"], errors="coerce")
    df = df.dropna(subset=["Cases", "Deaths"])
    
    grouped = df.groupby("Location").agg({"Cases": "sum", "Deaths": "sum"}).reset_index()
    grouped = grouped.sort_values("Cases", ascending=False)
    
    if len(grouped) > 20:
        grouped = grouped.head(20)
    
    return jsonify({
        "locations": grouped["Location"].tolist(),
        "cases": grouped["Cases"].astype(int).tolist(),
        "deaths": grouped["Deaths"].astype(int).tolist()
    })

@app.route("/api/regions")
def get_regions():
    island_group = request.args.get("island_group", "All Island Groups")
    df = load_data_by_island(island_group if island_group != "All Island Groups" else None)
    regions = sorted(df["Region"].unique()) if not df.empty else []
    return jsonify(regions)

    # =============================================================
@app.route("/api/summary")
def get_summary():
    try:
        year = request.args.get("year", None)
        metric = request.args.get("metric", "Cases")
        
        df = load_all_data()
        df[metric] = pd.to_numeric(df[metric], errors="coerce")
        df = df.dropna(subset=[metric])
        
        # Island group calculations
        island_totals = []
        for island in ["Luzon", "Visayas", "Mindanao"]:
            island_df = load_data_by_island(island)
            if year and year.lower() != "all":
                island_df = island_df[island_df["Year"] == int(year)]
            total = pd.to_numeric(island_df[metric], errors="coerce").sum()
            island_totals.append({
                "island": island,
                "total": int(total)
            })
        
        # Main total calculation
        if year and year.lower() != "all":
            current_year_df = df[df["Year"] == int(year)]
            total = current_year_df[metric].sum()
        else:
            total = df[metric].sum()
        
        # Enhanced year-over-year calculation
        comparison_data = None
        if year and year.lower() != "all":
            current_year = int(year)
            prev_year = current_year - 1
            
            current_data = df[df["Year"] == current_year]
            prev_data = df[df["Year"] == prev_year]
            
            current_total = current_data[metric].sum()
            prev_total = prev_data[metric].sum()
            
            if not prev_data.empty and prev_total > 0:
                change = current_total - prev_total
                percent_change = (change / prev_total) * 100
                
                comparison_data = {
                    "current_year": current_year,
                    "current_total": int(current_total),
                    "prev_year": prev_year,
                    "prev_total": int(prev_total),
                    "change_amount": int(change),
                    "percent_change": round(percent_change, 2),
                    "trend": "increase" if change >= 0 else "decrease"
                }
        
        return jsonify({
            "total": int(total),
            "metric": metric,
            "year": year if year else "All Years",
            "island_totals": island_totals,
            "is_all_years": year.lower() == "all" if year else True,
            "comparison": comparison_data
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/about')
def about():
    return render_template('about.html')  # New about page

if __name__ == "__main__":
    app.run(debug=True)