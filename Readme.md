Copie db.sqlite3 --> Conteneur

docker cp ".\web\db.sqlite3" "$(docker compose ps -q web):/data/db.sqlite3"
docker compose restart web

Import --> Local
docker cp "$(docker compose ps -q web):/data/db.sqlite3" "./db.from_container.sqlite3"