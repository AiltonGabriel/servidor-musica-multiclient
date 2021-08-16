class Music:
    def __init__(self, title, artist, duration):
        self.title = title
        self.artist = artist
        self.duration = duration
    def __str__(self):
        return self.title + ' - ' + self.artist

    def __repr__(self):
        return self.get_duration_str() + ' - ' +self.title + ' - ' + self.artist

    def get_duration_str(self):
        return ("{:02d}:{:02d}".format(int(self.duration / 60), int(self.duration % 60)))