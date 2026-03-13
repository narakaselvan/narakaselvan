SELECT
    a.preload_a1a AS district_name,
    
    COUNT(a.meta_id) AS total_assignments,
    
    COUNT(CASE WHEN a.meta_interviewscount != 0 THEN a.meta_id END) AS total_interviews_done,
    
    COUNT(CASE WHEN a.meta_receivedbytabletatutc IS NOT NULL THEN a.meta_id END) AS total_received,
    
    COUNT(DISTINCT CASE WHEN u.role='supervisor' THEN a.meta_responsiblename END) AS total_supervisors,
    
    COUNT(DISTINCT CASE WHEN u.role='interviewer' THEN a.meta_responsiblename END) AS total_interviewers,
    
    COUNT(CASE WHEN u.role='supervisor' THEN a.meta_id END) AS assignments_with_supervisors,
    
    COUNT(CASE WHEN u.role='interviewer' THEN a.meta_id END) AS assignments_with_interviewers,
    
    COUNT(DISTINCT a.preload_a0 || a.preload_a01) AS total_blocks

FROM assignments a
JOIN susouser u
  ON LEFT(u.workingarea::text,1) = LEFT(a.preload_a1b::text,1)
  AND u.login = a.meta_responsiblename
WHERE u.role IN ('supervisor', 'interviewer')
GROUP BY a.preload_a1a
ORDER BY a.preload_a1a;