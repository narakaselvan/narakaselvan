select a.meta_id, preload_a2b
FROM assignments a
    LEFT JOIN susouser u
      ON u.login = a.meta_responsiblename

    WHERE LEFT(u.workingarea::text,2) = LEFT(a.preload_a2b::text,2)
        AND LEFT(a.preload_a2b::text,2) = '11'

    GROUP BY preload_a3b, preload_a2a, meta_id
    ORDER BY preload_a3b;