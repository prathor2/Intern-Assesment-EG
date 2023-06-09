import pandas as pd
import numpy as np
from shapely.geometry import Polygon, Point

class ProcessGameState:
    def __init__(self, parquet_file, boundary_vertices):
        """
        Initialize the class with game data and boundary vertices
        :param parquet_file: The game data file in Parquet format
        :param boundary_vertices: The vertices of the polygonal boundary
        """
        self.data = pd.read_parquet(parquet_file)  # Load data
        self.polygon = Polygon(boundary_vertices)  # Create polygon
        # Run initial data processing
        self.filter_rows_in_boundary()
        self.extract_weapon_classes()


    def filter_rows_in_boundary(self):
        """
        Assign True or False to each row depending on whether the point is within the boundary and Z-Axis Bounds
        """
        xy_coords = list(zip(self.data['x'], self.data['y']))
        self.data['in_boundary'] = np.logical_and(
            np.array([self.polygon.contains(Point(point)) for point in xy_coords]),
            np.logical_and(self.data['z'] >= 285, self.data['z'] <= 421) 
        )
    
    def extract_weapon_classes(self): 
        """
        Extracts weapon classes from the inventory column and adds it as a new column
        Raises ValueError if the 'inventory' column is not in the DataFrame
        """
        if 'inventory' not in self.data.columns:
            raise ValueError("Missing 'inventory' column in DataFrame")

        def extract_classes(inventory_list): 
            """
            Helper function to extract classes from inventory list of dictionaries
            """
            if inventory_list is None:
                return []
            try:
                return [item['class'] for item in inventory_list]
            except KeyError:
                return []
        self.data['weapon_classes'] = self.data['inventory'].apply(extract_classes)

    def team_strategy(self, team, side):
        """
        Calculates the mean of in_boundary values for the given team and side
        :param team: The team to analyze
        :param side: The side (T or CT) to analyze
        """
        team_data = self.data[(self.data['team'] == team) & (self.data['side'] == side)]
        if team_data.empty:
            return "No data available for the given team and side"

        return team_data['in_boundary'].mean()

    def average_timer_with_weapons(self, team, side, min_weapons, weapon_types):
        """
        Calculates the average timer for the given team and side with at least min_weapons of weapon_types
        :param team: The team to analyze
        :param side: The side (T or CT) to analyze
        :param min_weapons: The minimum number of specified weapon types
        :param weapon_types: The types of weapons to consider
        """
        try:
            team_data = self.data[(self.data['team'] == team) & (self.data['side'] == side)]
            team_data = team_data.assign(weapon_count=team_data['weapon_classes'].apply(lambda x: sum([weapon in x for weapon in weapon_types])))
            filtered_data = team_data[team_data['weapon_count'] >= min_weapons]
            
            while filtered_data.empty and min_weapons > 0:
                min_weapons -= 1
                filtered_data = team_data[team_data['weapon_count'] >= min_weapons]
        except KeyError as e:
            return f"Error: {e} not found in data"
    
        except Exception as e:
            return f"Unexpected error: {e}"
      
        if filtered_data.empty:
            return "No data available for the given conditions"
    
        return filtered_data['seconds'].mean()
    
      


    def heatmap_coordinates(self, team, side):
        """
        Generates a heatmap of coordinates for the given team and side
        :param team: The team to analyze
        :param side: The side (T or CT) to analyze
        """
        team_data = self.data[(self.data['team'] == team) & (self.data['side'] == side) & (self.data['in_boundary'])]
        if team_data.empty:
            return "No data available for the given team and side"

        bins = 10  
        heatmap_data = team_data.groupby([pd.cut(team_data["x"], bins), pd.cut(team_data["y"], bins)]).size().unstack()
        return heatmap_data
  
