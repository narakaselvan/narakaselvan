    SELECT
        a.preload_a2b AS division_code,
        a.preload_a2a AS division_name,
        
        COUNT(a.meta_id) AS total_assignments,
        COUNT(CASE WHEN a.meta_interviewscount != 0 THEN a.meta_id END) AS total_interviews_done,
        COUNT(CASE WHEN a.meta_receivedbytabletatutc IS NOT NULL THEN a.meta_id END) AS total_received,
        
        COUNT(DISTINCT CASE WHEN u.role='supervisor' THEN a.meta_responsiblename END) AS total_supervisors,
        COUNT(DISTINCT CASE WHEN u.role='interviewer' THEN a.meta_responsiblename END) AS total_interviewers,
        
        COUNT(CASE WHEN u.role='supervisor' THEN a.meta_id END) AS assignments_with_supervisors,
        COUNT(CASE WHEN u.role='interviewer' THEN a.meta_id END) AS assignments_with_interviewers,
        
        COUNT(DISTINCT a.preload_a0 || a.preload_a01) AS total_blocks

    FROM assignments a
    LEFT JOIN susouser u
      ON u.login = a.meta_responsiblename

    WHERE LEFT(u.workingarea::text,2) = LEFT(a.preload_a2b::text,2)
        AND LEFT(a.preload_a2b::text,2) = '11'

    GROUP BY division_code, division_name
    ORDER BY division_code;