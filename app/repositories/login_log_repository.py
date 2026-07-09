from app.models.login_log import LoginLog


class LoginLogRepository:

    def __init__(self, db):
        self.db = db

    def create(self, log: LoginLog):
        self.db.add(log)