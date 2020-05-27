class TrackableObject:
    def __intit__(self, id, centroid):
        self.id = id
        self.centroid = [centroid]
        self.counted = False
