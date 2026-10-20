select sigla as ferrovia, nome, grupo_economico
from {{ ref('ferrovias') }}
