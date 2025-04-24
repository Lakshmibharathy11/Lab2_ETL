{% snapshot district_response_snapshot %}

{{
    config(
        target_schema='snapshots',
        unique_key='police_district',
        strategy='check',
        check_cols=['avg_response_time_min', 'total_cases']
    )
}}

WITH district_performance AS (
    SELECT 
        police_district,
        AVG(dispatch_to_received_min + onscene_to_enroute_min) AS avg_response_time_min
    FROM {{ ref('law_enforcement_calls') }}
    WHERE dispatch_to_received_min IS NOT NULL 
      AND onscene_to_enroute_min IS NOT NULL
    GROUP BY police_district
),

district_cases AS (
    SELECT 
        police_district, 
        COUNT(cad_number) AS total_cases
    FROM {{ ref('law_enforcement_calls') }}
    WHERE cad_number IS NOT NULL
    GROUP BY police_district
)

SELECT 
    perf.police_district,
    perf.avg_response_time_min,
    cases.total_cases
FROM district_performance perf
JOIN district_cases cases
    ON perf.police_district = cases.police_district

{% endsnapshot %}