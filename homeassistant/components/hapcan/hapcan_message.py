class HapcanMessage:
    def __init__(self, frame):
        self.frame = bytes(frame)
        self.frame_type = (frame[1] << 4) + (frame[2] >> 4)
        self.is_answer = (frame[2] & 0x01) != 0
        self.node = frame[3]
        self.group = frame[4]
