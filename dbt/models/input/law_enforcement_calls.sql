WITH law_data AS (
    SELECT *
    FROM {{ source('raw', 'law_enforcement_calls') }}
)

SELECT * FROM law_data












