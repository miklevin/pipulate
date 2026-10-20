SELECT 
    CASE
        WHEN ua.value LIKE 'Claude-User (claude-code/%'
        THEN 'Claude-User (claude-code/*; +https://support.anthropic.com/)'
        ELSE ua.value
    END as agent, 
    SUM(t.count) as total_reads
FROM telemetry t
JOIN ips i ON t.ip_id = i.id
JOIN paths p ON t.path_id = p.id
JOIN user_agents ua ON t.ua_id = ua.id
JOIN accept_headers ah ON t.accept_id = ah.id
WHERE t.served_md = 1
  AND ah.value LIKE '%text/markdown%'
  AND p.value LIKE '%src=content_neg%'
  AND i.value NOT LIKE '127.%'
  AND i.value NOT LIKE '10.%'
  AND i.value NOT LIKE '192.168.%'
  AND ua.value NOT LIKE '%Nexus 5X%'
  AND ua.value NOT LIKE '%Google-InspectionTool%'
  AND ua.value NOT LIKE '%Ubuntu%'
  AND ua.value NOT LIKE '%iPad%'
  AND ua.value NOT LIKE 'python-httpx%'
  AND ua.value NOT LIKE 'Go-http-client%'
  AND NOT (
      ua.value LIKE 'Mozilla%'
      AND ua.value NOT LIKE '%compatible%'
      AND (
          ua.value LIKE '%Windows NT%' OR
          ua.value LIKE '%Macintosh%' OR
          ua.value LIKE '%X11%' OR
          ua.value LIKE '%iPhone%' OR
          ua.value LIKE '%iPad%' OR
          ua.value LIKE '%Android%'
      )
  )
GROUP BY agent
ORDER BY total_reads DESC;