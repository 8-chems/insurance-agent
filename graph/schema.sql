-- Spanner Graph schema for the insurance assistant (apply with: gcloud spanner databases ddl update --ddl-file=graph/schema.sql)
-- Keys are random UUID strings (never sequential numbers) to avoid write hotspots.
-- Only ids and relationship attributes live here; names, addresses and documents stay in the source systems.

CREATE TABLE Customer (
  customer_id STRING(36) NOT NULL,
  region STRING(8),
  source_updated_at TIMESTAMP NOT NULL,
) PRIMARY KEY (customer_id);

CREATE TABLE Policy (
  policy_id STRING(36) NOT NULL,
  product STRING(32),
  source_updated_at TIMESTAMP NOT NULL,
) PRIMARY KEY (policy_id);

CREATE TABLE PolicyVersion (
  policy_version_id STRING(64) NOT NULL,
  policy_id STRING(36) NOT NULL,
  version INT64 NOT NULL,
  document_id STRING(64) NOT NULL,        -- joins to kb.chunks.document_id from Part 2
  effective_from DATE NOT NULL,
  effective_to DATE,
  source_updated_at TIMESTAMP NOT NULL,
) PRIMARY KEY (policy_version_id);

CREATE TABLE Claim (
  claim_id STRING(36) NOT NULL,
  status STRING(16),
  service_date DATE,
  submitted_at TIMESTAMP,
  source_updated_at TIMESTAMP NOT NULL,
) PRIMARY KEY (claim_id);

CREATE TABLE Provider (
  provider_id STRING(36) NOT NULL,
  source_updated_at TIMESTAMP NOT NULL,
) PRIMARY KEY (provider_id);

CREATE TABLE ProviderGroup (
  group_id STRING(36) NOT NULL,
  source_updated_at TIMESTAMP NOT NULL,
) PRIMARY KEY (group_id);

-- Edge tables are interleaved in their SOURCE node's table so forward traversal reads co-located rows.
CREATE TABLE CustomerOwnsPolicy (
  customer_id STRING(36) NOT NULL,
  policy_id STRING(36) NOT NULL,
  source_updated_at TIMESTAMP NOT NULL,
) PRIMARY KEY (customer_id, policy_id),
  INTERLEAVE IN PARENT Customer ON DELETE CASCADE;

CREATE TABLE PolicyHasVersion (
  policy_id STRING(36) NOT NULL,
  policy_version_id STRING(64) NOT NULL,
  source_updated_at TIMESTAMP NOT NULL,
) PRIMARY KEY (policy_id, policy_version_id),
  INTERLEAVE IN PARENT Policy ON DELETE CASCADE;

CREATE TABLE PolicyHasClaim (
  policy_id STRING(36) NOT NULL,
  claim_id STRING(36) NOT NULL,
  source_updated_at TIMESTAMP NOT NULL,
) PRIMARY KEY (policy_id, claim_id),
  INTERLEAVE IN PARENT Policy ON DELETE CASCADE;

CREATE TABLE ClaimByProvider (
  claim_id STRING(36) NOT NULL,
  provider_id STRING(36) NOT NULL,
  source_updated_at TIMESTAMP NOT NULL,
) PRIMARY KEY (claim_id, provider_id),
  INTERLEAVE IN PARENT Claim ON DELETE CASCADE;

CREATE TABLE ProviderMemberOf (
  provider_id STRING(36) NOT NULL,
  group_id STRING(36) NOT NULL,
  source_updated_at TIMESTAMP NOT NULL,
) PRIMARY KEY (provider_id, group_id),
  INTERLEAVE IN PARENT Provider ON DELETE CASCADE;

-- DERIVED edge: written by a rule (graph/derive_applies_version.sql), never by source events.
-- rule_id and derived_at make every inference explainable and recomputable.
CREATE TABLE ClaimAppliesVersion (
  claim_id STRING(36) NOT NULL,
  policy_version_id STRING(64) NOT NULL,
  rule_id STRING(64) NOT NULL,
  derived_at TIMESTAMP NOT NULL,
) PRIMARY KEY (claim_id, policy_version_id),
  INTERLEAVE IN PARENT Claim ON DELETE CASCADE;

-- Reverse traversal (child -> parent) needs interleaved indexes on the destination side.
CREATE INDEX PolicyOwnerByPolicy ON CustomerOwnsPolicy (policy_id, customer_id), INTERLEAVE IN Policy;
CREATE INDEX ClaimPolicyByClaim ON PolicyHasClaim (claim_id, policy_id), INTERLEAVE IN Claim;

CREATE PROPERTY GRAPH InsuranceGraph
  NODE TABLES (Customer, Policy, PolicyVersion, Claim, Provider, ProviderGroup)
  EDGE TABLES (
    CustomerOwnsPolicy SOURCE KEY (customer_id) REFERENCES Customer (customer_id)
      DESTINATION KEY (policy_id) REFERENCES Policy (policy_id) LABEL Owns,
    PolicyHasVersion SOURCE KEY (policy_id) REFERENCES Policy (policy_id)
      DESTINATION KEY (policy_version_id) REFERENCES PolicyVersion (policy_version_id) LABEL HasVersion,
    PolicyHasClaim SOURCE KEY (policy_id) REFERENCES Policy (policy_id)
      DESTINATION KEY (claim_id) REFERENCES Claim (claim_id) LABEL HasClaim,
    ClaimByProvider SOURCE KEY (claim_id) REFERENCES Claim (claim_id)
      DESTINATION KEY (provider_id) REFERENCES Provider (provider_id) LABEL ByProvider,
    ProviderMemberOf SOURCE KEY (provider_id) REFERENCES Provider (provider_id)
      DESTINATION KEY (group_id) REFERENCES ProviderGroup (group_id) LABEL MemberOf,
    ClaimAppliesVersion SOURCE KEY (claim_id) REFERENCES Claim (claim_id)
      DESTINATION KEY (policy_version_id) REFERENCES PolicyVersion (policy_version_id) LABEL AppliesVersion
  );
