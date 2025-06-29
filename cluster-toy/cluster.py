import numpy as np
from sklearn.cluster import DBSCAN
from math import radians, sin, cos, sqrt, atan2

def haversine_distance(coord1, coord2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    Returns distance in kilometers
    """
    lat1, lon1 = radians(coord1[0]), radians(coord1[1])
    lat2, lon2 = radians(coord2[0]), radians(coord2[1])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    # Earth's radius in kilometers
    R = 6371.0
    return R * c

def cluster_coordinates_dbscan(coordinates, eps_km=1.0, min_samples=3):
    """
    Cluster geographic coordinates using DBSCAN algorithm.
    
    Parameters:
    -----------
    coordinates : list of tuples or list of lists
        List of (latitude, longitude) pairs in decimal degrees
    eps_km : float, default=1.0
        Maximum distance (in kilometers) between points to be considered neighbors
    min_samples : int, default=3
        Minimum number of points required to form a cluster
    
    Returns:
    --------
    dict : Dictionary containing:
        - 'labels': array of cluster labels (-1 for noise/outliers)
        - 'clusters': dictionary mapping cluster_id to list of coordinate indices
        - 'outliers': list of indices for outlier points
        - 'n_clusters': number of clusters found
    """
    
    if not coordinates:
        return {
            'labels': np.array([]),
            'clusters': {},
            'outliers': [],
            'n_clusters': 0
        }
    
    # Convert to numpy array for easier handling
    coords_array = np.array(coordinates)
    n_points = len(coords_array)
    
    # Create distance matrix using haversine distance
    distance_matrix = np.zeros((n_points, n_points))
    
    for i in range(n_points):
        for j in range(i+1, n_points):
            dist = haversine_distance(coords_array[i], coords_array[j])
            distance_matrix[i][j] = dist
            distance_matrix[j][i] = dist
    
    # Apply DBSCAN clustering
    dbscan = DBSCAN(eps=eps_km, min_samples=min_samples, metric='precomputed')
    cluster_labels = dbscan.fit_predict(distance_matrix)
    
    # Organize results
    clusters = {}
    outliers = []
    
    for idx, label in enumerate(cluster_labels):
        if label == -1:
            outliers.append(idx)
        else:
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(idx)
    
    n_clusters = len(clusters)
    
    return {
        'labels': cluster_labels,
        'clusters': clusters,
        'outliers': outliers,
        'n_clusters': n_clusters
    }

def print_clustering_results(coordinates, results):
    """
    Helper function to print clustering results in a readable format.
    
    Parameters:
    -----------
    coordinates : list
        Original list of coordinates
    results : dict
        Results from cluster_coordinates_dbscan function
    """
    print(f"Found {results['n_clusters']} clusters")
    print(f"Found {len(results['outliers'])} outliers")
    print("-" * 50)
    
    # Print clusters
    for cluster_id, indices in results['clusters'].items():
        print(f"Cluster {cluster_id}: {len(indices)} points")
        for idx in indices:
            lat, lon = coordinates[idx]
            print(f"  Point {idx}: ({lat:.6f}, {lon:.6f})")
        print()
    
    # Print outliers
    if results['outliers']:
        print("Outliers:")
        for idx in results['outliers']:
            lat, lon = coordinates[idx]
            print(f"  Point {idx}: ({lat:.6f}, {lon:.6f})")

# Example usage
if __name__ == "__main__":
    # Sample coordinates (latitude, longitude) - mix of clusters and outliers
    sample_coordinates = [
        (40.7128, -74.0060),  # NYC area
        (40.7614, -73.9776),  # NYC area
        (40.7505, -73.9934),  # NYC area
        (34.0522, -118.2437), # LA area
        (34.0928, -118.3287), # LA area
        (41.8781, -87.6298),  # Chicago area
        (41.8819, -87.6278),  # Chicago area
        (25.7617, -80.1918),  # Miami (outlier)
    ]
    
    # Cluster the coordinates
    results = cluster_coordinates_dbscan(
        sample_coordinates, 
        eps_km=50.0,  # 50km radius
        min_samples=2  # At least 2 points per cluster
    )
    
    # Print results
    print_clustering_results(sample_coordinates, results)
