export const FeatureCode = {
  STUDENTS_MANAGE: 'students.manage',
  STAFF_MANAGE: 'staff.manage',
  CLASSES_MANAGE: 'classes.manage',
  RESULTS_MANAGE: 'results.manage',
  FINANCE_INVOICING: 'finance.invoicing',
  MEDICAL_RECORDS: 'medical.records',
  LIBRARY_CIRCULATION: 'library.circulation',
  TRANSPORT_ROUTES: 'transport.routes',
  HOSTEL_MANAGE: 'hostel.manage',
  STUDENT_LIFE_ACTIVITIES: 'student_life.activities',
  QUOTA_ACTIVE_STUDENTS: 'quota.active_students',
  QUOTA_ACTIVE_STAFF: 'quota.active_staff',
} as const;

export type FeatureCodeValue = (typeof FeatureCode)[keyof typeof FeatureCode] | string;

export interface EffectiveEntitlements {
  tenant_id: string;
  subscription_id: string;
  plan_code: string;
  status: string;
  can_read: boolean;
  can_write: boolean;
  entitlement_version: number;
  values: Record<string, boolean | number | string | object | null>;
}

export interface UsageItem {
  feature_code: string;
  limit: number;
  current_usage: number;
  percent_used: number;
}
