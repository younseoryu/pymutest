import random
def kmeans_1d(data, k=2, max_iterations=100):
    # Initialize centroids to k random x coordinates from the data
    centroids = [data[i] for i in sorted(random.sample(range(len(data)), k))]
    
    for iteration in range(max_iterations):
        clusters = [[] for _ in range(k)]
        
        # Assign data points to the closest centroid
        for x in data:
            distances = [abs(x - centroid) for centroid in centroids]
            closest_centroid = distances.index(min(distances))
            clusters[closest_centroid].append(x)
        
        # Calculate new centroids as the mean of the points in each cluster
        new_centroids = []
        for cluster in clusters:
            if cluster:  # Avoid division by zero
                new_centroids.append(sum(cluster) / len(cluster))
            else:  # Handle empty cluster
                new_centroids.append(random.choice(data))
        
        # Check for convergence (if centroids do not change)
        if new_centroids == centroids:
            break
        centroids = new_centroids
    
    # Assign cluster index to each data point based on closest centroid
    cluster_labels = []
    for x in data:
        distances = [abs(x - centroid) for centroid in centroids]
        closest_centroid = distances.index(min(distances))
        cluster_labels.append(closest_centroid)
    # print("centroids:", centroids)
    return centroids, cluster_labels
