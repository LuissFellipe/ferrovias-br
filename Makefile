.PHONY: up ingest patios producao transform export docs site analise pipeline down

up:
	docker compose up -d --wait

patios:
	uv run python ingest/ingest_patios.py

producao:
	uv run python ingest/ingest_producao.py

ingest: patios producao

transform:
	cd dbt_ferrovias && uv run dbt deps --profiles-dir . && uv run dbt build --profiles-dir .

export:
	uv run python export/export_site.py

pipeline: up ingest transform export

# Documentação do dbt como página estática, publicada junto com o painel em /dbt/.
docs:
	cd dbt_ferrovias && uv run dbt docs generate --static --profiles-dir .
	mkdir -p site/dbt && cp dbt_ferrovias/target/static_index.html site/dbt/index.html

site: export
	@echo "abra http://localhost:8001"
	uv run python -m http.server 8001 -d site

analise:
	uv run --group analise jupyter lab analises/

down:
	docker compose down
