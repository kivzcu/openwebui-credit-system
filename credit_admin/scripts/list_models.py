import json
from app.database import db


def main():
    models = db.get_all_models()
    print(json.dumps(models, indent=2, default=str))
    print(db.db_type)


if __name__ == '__main__':
    main()


# credit_system_db