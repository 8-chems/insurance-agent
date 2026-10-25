-- Rule version_by_service_date_v1: a claim is governed by the policy version whose validity
-- interval contains the claim's service date. Run for claims changed since @since (batch it by claim id range).
-- Step 1 removes edges this rule produced earlier for those claims, so a corrected date cannot leave a stale edge.
DELETE FROM ClaimAppliesVersion
WHERE rule_id = 'version_by_service_date_v1'
  AND claim_id IN (SELECT claim_id FROM Claim WHERE source_updated_at >= @since);

INSERT INTO ClaimAppliesVersion (claim_id, policy_version_id, rule_id, derived_at)
SELECT cl.claim_id, v.policy_version_id, 'version_by_service_date_v1', CURRENT_TIMESTAMP()
FROM Claim cl
JOIN PolicyHasClaim phc ON phc.claim_id = cl.claim_id
JOIN PolicyHasVersion phv ON phv.policy_id = phc.policy_id
JOIN PolicyVersion v ON v.policy_version_id = phv.policy_version_id
WHERE cl.source_updated_at >= @since
  AND v.effective_from <= cl.service_date
  AND (v.effective_to IS NULL OR v.effective_to >= cl.service_date);
