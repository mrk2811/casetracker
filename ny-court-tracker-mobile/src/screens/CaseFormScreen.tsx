import React, { useState, useEffect } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TextInput,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  Linking,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { casesApi, CaseSearchResult } from "../services/api";

const COURT_TYPES = [
  { value: "supreme", label: "Civil Supreme Court" },
  { value: "local_civil", label: "Local Civil Court" },
  { value: "criminal", label: "Criminal Court" },
];

const STATUSES = [
  { value: "active", label: "Active" },
  { value: "pending", label: "Pending" },
  { value: "disposed", label: "Disposed" },
];

const PRIORITIES = [
  { value: "normal", label: "Normal", description: "Updated 2x/day (6am, 12:30pm)" },
  { value: "high", label: "High Priority", description: "Updated every 2-4 hours" },
];

const NY_COUNTIES = [
  "Albany", "Allegany", "Bronx", "Broome", "Cattaraugus", "Cayuga", "Chautauqua",
  "Chemung", "Chenango", "Clinton", "Columbia", "Cortland", "Delaware", "Dutchess",
  "Erie", "Essex", "Franklin", "Fulton", "Genesee", "Greene", "Hamilton", "Herkimer",
  "Jefferson", "Kings", "Lewis", "Livingston", "Madison", "Monroe", "Montgomery",
  "Nassau", "New York", "Niagara", "Oneida", "Onondaga", "Ontario", "Orange",
  "Orleans", "Oswego", "Otsego", "Putnam", "Queens", "Rensselaer", "Richmond",
  "Rockland", "Saratoga", "Schenectady", "Schoharie", "Schuyler", "Seneca",
  "St. Lawrence", "Steuben", "Suffolk", "Sullivan", "Tioga", "Tompkins", "Ulster",
  "Warren", "Washington", "Wayne", "Westchester", "Wyoming", "Yates",
];

function getCourtSystem(courtType: string): string {
  if (courtType === "criminal") return "ny_webcrimin";
  return "ny_webcivil";
}

export default function CaseFormScreen({ route, navigation }: any) {
  const editId = route.params?.id;
  const isEditing = !!editId;

  const [form, setForm] = useState({
    court_type: "supreme",
    county: "",
    index_number: "",
    case_year: "",
    case_status: "active",
    priority: "normal",
    plaintiff: "",
    defendant: "",
    plaintiff_firm: "",
    defendant_firm: "",
    justice: "",
    part: "",
    notes: "",
  });
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showCourtPicker, setShowCourtPicker] = useState(false);
  const [showCountyPicker, setShowCountyPicker] = useState(false);
  const [showStatusPicker, setShowStatusPicker] = useState(false);
  const [showPriorityPicker, setShowPriorityPicker] = useState(false);

  // Verification flow state
  const [searching, setSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<CaseSearchResult[]>([]);
  const [searchMessage, setSearchMessage] = useState<string | null>(null);
  const [showVerification, setShowVerification] = useState(false);
  const [selectedResult, setSelectedResult] = useState<CaseSearchResult | null>(null);

  // Captcha / WebCivil redirect flow state
  const [showCaptchaRedirect, setShowCaptchaRedirect] = useState(false);

  useEffect(() => {
    if (isEditing) {
      setLoading(true);
      casesApi
        .get(editId)
        .then((res) => {
          const c = res.data;
          setForm({
            court_type: c.court_type,
            county: c.county,
            index_number: c.index_number,
            case_year: c.case_year ? String(c.case_year) : "",
            case_status: c.case_status,
            priority: c.priority || "normal",
            plaintiff: c.plaintiff || "",
            defendant: c.defendant || "",
            plaintiff_firm: c.plaintiff_firm || "",
            defendant_firm: c.defendant_firm || "",
            justice: c.justice || "",
            part: c.part || "",
            notes: c.notes || "",
          });
        })
        .catch(() => Alert.alert("Error", "Failed to load case"))
        .finally(() => setLoading(false));
    }
  }, [editId]);

  const updateForm = (key: string, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleSearch = async () => {
    if (!form.index_number || !form.county) {
      Alert.alert("Required Fields", "Please enter an Index Number and select a County before searching.");
      return;
    }
    setSearching(true);
    setSearchResults([]);
    setSearchMessage(null);
    setSelectedResult(null);
    setShowCaptchaRedirect(false);
    try {
      const courtSystem = getCourtSystem(form.court_type);
      const res = await casesApi.search({
        index_number: form.index_number,
        court_type: form.court_type,
        county: form.county,
        court_system: courtSystem,
      });

      // Check if backend says captcha is required
      if (res.data.captcha_required) {
        setShowCaptchaRedirect(true);
        setSearchMessage(res.data.message);
        return;
      }

      setSearchResults(res.data.results);
      setSearchMessage(res.data.message);
      setShowVerification(true);
    } catch (err: any) {
      const msg = err.response?.data?.detail || "Failed to search court system";
      Alert.alert("Search Error", msg);
    } finally {
      setSearching(false);
    }
  };

  const getWebCivilSearchUrl = (): string => {
    // Build a direct link to the WebCivil search page based on court type
    if (form.court_type === "local_civil") {
      return "https://iapps.courts.state.ny.us/webcivilLocal/LCSearch?param=I";
    }
    return "https://iapps.courts.state.ny.us/webcivil/FCASSearch?param=I";
  };

  const handleOpenWebCivil = () => {
    Linking.openURL(getWebCivilSearchUrl());
  };

  const handleSelectResult = (result: CaseSearchResult) => {
    setSelectedResult(result);
    setForm((prev) => ({
      ...prev,
      index_number: result.index_number || prev.index_number,
      court_type: result.court_type || prev.court_type,
      county: result.county || prev.county,
      case_year: result.case_year ? String(result.case_year) : prev.case_year,
      case_status: result.case_status || prev.case_status,
      plaintiff: result.plaintiff || prev.plaintiff,
      defendant: result.defendant || prev.defendant,
      plaintiff_firm: result.plaintiff_firm || prev.plaintiff_firm,
      defendant_firm: result.defendant_firm || prev.defendant_firm,
      justice: result.justice || prev.justice,
      part: result.part || prev.part,
    }));
  };

  const handleVerifiedSubmit = async () => {
    if (!selectedResult) return;
    setSaving(true);
    try {
      const courtSystem = getCourtSystem(form.court_type);
      await casesApi.verify({
        court_type: form.court_type,
        county: form.county,
        index_number: form.index_number,
        case_year: form.case_year ? parseInt(form.case_year) : null,
        case_status: form.case_status,
        priority: form.priority,
        plaintiff: form.plaintiff || null,
        defendant: form.defendant || null,
        plaintiff_firm: form.plaintiff_firm || null,
        defendant_firm: form.defendant_firm || null,
        justice: form.justice || null,
        part: form.part || null,
        notes: form.notes || null,
        court_system: courtSystem,
        search_params: JSON.stringify({
          index_number: form.index_number,
          county: form.county,
          court_type: form.court_type,
        }),
      });
      navigation.goBack();
    } catch (err: any) {
      const msg = err.response?.data?.detail || "Failed to save verified case";
      Alert.alert("Error", msg);
    } finally {
      setSaving(false);
    }
  };

  const handleSubmit = async () => {
    if (!form.county || !form.index_number) {
      Alert.alert("Error", "County and Index Number are required");
      return;
    }
    setSaving(true);
    try {
      const data: any = {
        court_type: form.court_type,
        county: form.county,
        index_number: form.index_number,
        case_status: form.case_status,
        priority: form.priority,
        case_year: form.case_year ? parseInt(form.case_year) : null,
        plaintiff: form.plaintiff || null,
        defendant: form.defendant || null,
        plaintiff_firm: form.plaintiff_firm || null,
        defendant_firm: form.defendant_firm || null,
        justice: form.justice || null,
        part: form.part || null,
        notes: form.notes || null,
      };

      if (isEditing) {
        await casesApi.update(editId, data);
      } else {
        await casesApi.create(data);
      }
      navigation.goBack();
    } catch (err: any) {
      const msg = err.response?.data?.detail || "Failed to save case";
      Alert.alert("Error", msg);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#18181b" />
      </View>
    );
  }

  const selectedCourt = COURT_TYPES.find((c) => c.value === form.court_type);
  const selectedStatus = STATUSES.find((s) => s.value === form.case_status);
  const selectedPriority = PRIORITIES.find((p) => p.value === form.priority);

  // Verification results view
  if (showVerification) {
    return (
      <ScrollView style={styles.container} keyboardShouldPersistTaps="handled">
        <TouchableOpacity
          style={styles.backButton}
          onPress={() => {
            setShowVerification(false);
            setSearchResults([]);
            setSelectedResult(null);
          }}
        >
          <Ionicons name="arrow-back" size={20} color="#18181b" />
          <Text style={styles.backButtonText}>Back to Form</Text>
        </TouchableOpacity>

        <Text style={styles.title}>Verify Case</Text>
        <Text style={styles.subtitle}>
          {searchMessage || "Review the search results below"}
        </Text>

        {searchResults.length === 0 ? (
          <View style={styles.noResults}>
            <Ionicons name="search-outline" size={40} color="#d1d5db" />
            <Text style={styles.noResultsTitle}>No Cases Found</Text>
            <Text style={styles.noResultsText}>
              The scraper could not find a matching case. You can still add it manually.
            </Text>
            <TouchableOpacity
              style={styles.manualButton}
              onPress={() => {
                setShowVerification(false);
                setSearchResults([]);
              }}
            >
              <Text style={styles.manualButtonText}>Add Manually</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <>
            {searchResults.map((result, index) => {
              const isSelected = selectedResult === result;
              return (
                <TouchableOpacity
                  key={index}
                  style={[styles.resultCard, isSelected && styles.resultCardSelected]}
                  onPress={() => handleSelectResult(result)}
                >
                  <View style={styles.resultHeader}>
                    <View style={styles.resultBadgeRow}>
                      <View style={styles.resultIndexBadge}>
                        <Text style={styles.resultIndexText}>{result.index_number}</Text>
                      </View>
                      {isSelected && (
                        <Ionicons name="checkmark-circle" size={20} color="#10b981" />
                      )}
                    </View>
                  </View>

                  {(result.plaintiff || result.defendant) && (
                    <Text style={styles.resultParties}>
                      {result.plaintiff || "Unknown"} v. {result.defendant || "Unknown"}
                    </Text>
                  )}

                  <View style={styles.resultDetails}>
                    {result.county && (
                      <View style={styles.resultDetailRow}>
                        <Text style={styles.resultDetailLabel}>County:</Text>
                        <Text style={styles.resultDetailValue}>{result.county}</Text>
                      </View>
                    )}
                    {result.justice && (
                      <View style={styles.resultDetailRow}>
                        <Text style={styles.resultDetailLabel}>Justice:</Text>
                        <Text style={styles.resultDetailValue}>{result.justice}</Text>
                      </View>
                    )}
                    {result.case_status && (
                      <View style={styles.resultDetailRow}>
                        <Text style={styles.resultDetailLabel}>Status:</Text>
                        <Text style={styles.resultDetailValue}>{result.case_status}</Text>
                      </View>
                    )}
                  </View>

                  {result.last_action && (
                    <View style={styles.lastActionBox}>
                      <Ionicons name="document-text-outline" size={14} color="#6b7280" />
                      <Text style={styles.lastActionText}>
                        Last Action: {result.last_action}
                        {result.last_action_date ? ` (${result.last_action_date})` : ""}
                      </Text>
                    </View>
                  )}

                  {isSelected && (
                    <Text style={styles.selectedHint}>
                      Does this match your case? Tap "Track This Case" below to confirm.
                    </Text>
                  )}
                </TouchableOpacity>
              );
            })}

            {selectedResult && (
              <View style={styles.verifyActions}>
                <TouchableOpacity
                  style={[styles.verifyButton, saving && styles.buttonDisabled]}
                  onPress={handleVerifiedSubmit}
                  disabled={saving}
                >
                  {saving ? (
                    <ActivityIndicator color="#fff" />
                  ) : (
                    <>
                      <Ionicons name="checkmark-circle" size={18} color="#fff" />
                      <Text style={styles.verifyButtonText}>Track This Case</Text>
                    </>
                  )}
                </TouchableOpacity>
                <TouchableOpacity
                  style={styles.manualButton}
                  onPress={() => {
                    setShowVerification(false);
                    setSearchResults([]);
                    setSelectedResult(null);
                  }}
                >
                  <Text style={styles.manualButtonText}>Edit Details First</Text>
                </TouchableOpacity>
              </View>
            )}
          </>
        )}

        <View style={{ height: 40 }} />
      </ScrollView>
    );
  }

  return (
    <ScrollView style={styles.container} keyboardShouldPersistTaps="handled">
      <Text style={styles.title}>{isEditing ? "Edit Case" : "Add New Case"}</Text>
      <Text style={styles.subtitle}>
        {isEditing ? "Update the case details" : "Enter the case details from the NY Court system"}
      </Text>

      {/* Court Information */}
      <Text style={styles.sectionTitle}>Court Information</Text>

      <Text style={styles.label}>Court Type</Text>
      <TouchableOpacity
        style={styles.picker}
        onPress={() => setShowCourtPicker(!showCourtPicker)}
      >
        <Text style={styles.pickerText}>{selectedCourt?.label}</Text>
        <Ionicons name="chevron-down" size={18} color="#6b7280" />
      </TouchableOpacity>
      {showCourtPicker && (
        <View style={styles.pickerOptions}>
          {COURT_TYPES.map((ct) => (
            <TouchableOpacity
              key={ct.value}
              style={[
                styles.pickerOption,
                form.court_type === ct.value && styles.pickerOptionSelected,
              ]}
              onPress={() => {
                updateForm("court_type", ct.value);
                setShowCourtPicker(false);
              }}
            >
              <Text
                style={[
                  styles.pickerOptionText,
                  form.court_type === ct.value && styles.pickerOptionTextSelected,
                ]}
              >
                {ct.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      )}

      <Text style={styles.label}>County *</Text>
      <TouchableOpacity
        style={styles.picker}
        onPress={() => setShowCountyPicker(!showCountyPicker)}
      >
        <Text style={[styles.pickerText, !form.county && { color: "#9ca3af" }]}>
          {form.county || "Select county"}
        </Text>
        <Ionicons name="chevron-down" size={18} color="#6b7280" />
      </TouchableOpacity>
      {showCountyPicker && (
        <ScrollView style={styles.pickerOptionsScroll} nestedScrollEnabled>
          {NY_COUNTIES.map((county) => (
            <TouchableOpacity
              key={county}
              style={[
                styles.pickerOption,
                form.county === county && styles.pickerOptionSelected,
              ]}
              onPress={() => {
                updateForm("county", county);
                setShowCountyPicker(false);
              }}
            >
              <Text
                style={[
                  styles.pickerOptionText,
                  form.county === county && styles.pickerOptionTextSelected,
                ]}
              >
                {county}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      )}

      <View style={styles.row}>
        <View style={styles.flex1}>
          <Text style={styles.label}>Index Number *</Text>
          <TextInput
            style={styles.input}
            value={form.index_number}
            onChangeText={(v) => updateForm("index_number", v)}
            placeholder="e.g. 123456"
            placeholderTextColor="#9ca3af"
          />
        </View>
        <View style={styles.flex1}>
          <Text style={styles.label}>Year</Text>
          <TextInput
            style={styles.input}
            value={form.case_year}
            onChangeText={(v) => updateForm("case_year", v)}
            placeholder="e.g. 2026"
            placeholderTextColor="#9ca3af"
            keyboardType="numeric"
          />
        </View>
      </View>

      {/* Search & Verify Button - only for new cases */}
      {!isEditing && (
        <TouchableOpacity
          style={[styles.searchButton, searching && styles.buttonDisabled]}
          onPress={() => handleSearch()}
          disabled={searching}
        >
          {searching ? (
            <ActivityIndicator color="#fff" size="small" />
          ) : (
            <>
              <Ionicons name="search" size={16} color="#fff" />
              <Text style={styles.searchButtonText}>Search & Verify Case</Text>
            </>
          )}
        </TouchableOpacity>
      )}

      {/* Captcha redirect — direct user to WebCivil */}
      {showCaptchaRedirect && (
        <View style={styles.captchaContainer}>
          <View style={styles.captchaHeader}>
            <Ionicons name="shield-checkmark-outline" size={20} color="#f59e0b" />
            <Text style={styles.captchaTitle}>Human Verification Required</Text>
          </View>
          <Text style={styles.captchaSubtitle}>
            The court website requires human verification that can only be
            completed on their site. Please search directly on WebCivil and
            then add the case manually below.
          </Text>

          <TouchableOpacity
            style={styles.openWebCivilButton}
            onPress={handleOpenWebCivil}
          >
            <Ionicons name="open-outline" size={16} color="#fff" />
            <Text style={styles.openWebCivilButtonText}>
              Open WebCivil Search
            </Text>
          </TouchableOpacity>

          <View style={styles.captchaSteps}>
            <Text style={styles.captchaStepText}>
              1. Click the button above to open WebCivil
            </Text>
            <Text style={styles.captchaStepText}>
              2. Search for your case ({form.index_number || "index number"})
            </Text>
            <Text style={styles.captchaStepText}>
              3. Note the case details (parties, status, etc.)
            </Text>
            <Text style={styles.captchaStepText}>
              4. Come back here and fill in the form below
            </Text>
          </View>

          <TouchableOpacity
            style={styles.dismissCaptchaButton}
            onPress={() => setShowCaptchaRedirect(false)}
          >
            <Text style={styles.dismissCaptchaText}>Got it, I'll fill in manually</Text>
          </TouchableOpacity>
        </View>
      )}

      {!isEditing && !showCaptchaRedirect && (
        <Text style={styles.searchHint}>
          Search the court system to verify and auto-fill case details, or fill in manually below.
        </Text>
      )}

      <Text style={styles.label}>Status</Text>
      <TouchableOpacity
        style={styles.picker}
        onPress={() => setShowStatusPicker(!showStatusPicker)}
      >
        <Text style={styles.pickerText}>{selectedStatus?.label}</Text>
        <Ionicons name="chevron-down" size={18} color="#6b7280" />
      </TouchableOpacity>
      {showStatusPicker && (
        <View style={styles.pickerOptions}>
          {STATUSES.map((s) => (
            <TouchableOpacity
              key={s.value}
              style={[
                styles.pickerOption,
                form.case_status === s.value && styles.pickerOptionSelected,
              ]}
              onPress={() => {
                updateForm("case_status", s.value);
                setShowStatusPicker(false);
              }}
            >
              <Text
                style={[
                  styles.pickerOptionText,
                  form.case_status === s.value && styles.pickerOptionTextSelected,
                ]}
              >
                {s.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      )}

      {/* Priority */}
      <Text style={styles.label}>Priority</Text>
      <TouchableOpacity
        style={styles.picker}
        onPress={() => setShowPriorityPicker(!showPriorityPicker)}
      >
        <View style={styles.priorityPickerContent}>
          {form.priority === "high" && (
            <Ionicons name="flag" size={14} color="#ef4444" />
          )}
          <Text style={styles.pickerText}>{selectedPriority?.label}</Text>
        </View>
        <Ionicons name="chevron-down" size={18} color="#6b7280" />
      </TouchableOpacity>
      {showPriorityPicker && (
        <View style={styles.pickerOptions}>
          {PRIORITIES.map((p) => (
            <TouchableOpacity
              key={p.value}
              style={[
                styles.pickerOption,
                form.priority === p.value && styles.pickerOptionSelected,
              ]}
              onPress={() => {
                updateForm("priority", p.value);
                setShowPriorityPicker(false);
              }}
            >
              <View>
                <Text
                  style={[
                    styles.pickerOptionText,
                    form.priority === p.value && styles.pickerOptionTextSelected,
                    p.value === "high" && { color: "#ef4444" },
                  ]}
                >
                  {p.value === "high" ? "\u{1F6A9} " : ""}{p.label}
                </Text>
                <Text style={styles.priorityDescription}>{p.description}</Text>
              </View>
            </TouchableOpacity>
          ))}
        </View>
      )}

      {/* Parties */}
      <Text style={styles.sectionTitle}>Parties</Text>

      <View style={styles.row}>
        <View style={styles.flex1}>
          <Text style={styles.label}>Plaintiff</Text>
          <TextInput
            style={styles.input}
            value={form.plaintiff}
            onChangeText={(v) => updateForm("plaintiff", v)}
            placeholderTextColor="#9ca3af"
          />
        </View>
        <View style={styles.flex1}>
          <Text style={styles.label}>Defendant</Text>
          <TextInput
            style={styles.input}
            value={form.defendant}
            onChangeText={(v) => updateForm("defendant", v)}
            placeholderTextColor="#9ca3af"
          />
        </View>
      </View>

      <View style={styles.row}>
        <View style={styles.flex1}>
          <Text style={styles.label}>Plaintiff Firm</Text>
          <TextInput
            style={styles.input}
            value={form.plaintiff_firm}
            onChangeText={(v) => updateForm("plaintiff_firm", v)}
            placeholderTextColor="#9ca3af"
          />
        </View>
        <View style={styles.flex1}>
          <Text style={styles.label}>Defendant Firm</Text>
          <TextInput
            style={styles.input}
            value={form.defendant_firm}
            onChangeText={(v) => updateForm("defendant_firm", v)}
            placeholderTextColor="#9ca3af"
          />
        </View>
      </View>

      {/* Court Details */}
      <Text style={styles.sectionTitle}>Court Details</Text>

      <View style={styles.row}>
        <View style={styles.flex1}>
          <Text style={styles.label}>Justice</Text>
          <TextInput
            style={styles.input}
            value={form.justice}
            onChangeText={(v) => updateForm("justice", v)}
            placeholderTextColor="#9ca3af"
          />
        </View>
        <View style={styles.flex1}>
          <Text style={styles.label}>Part</Text>
          <TextInput
            style={styles.input}
            value={form.part}
            onChangeText={(v) => updateForm("part", v)}
            placeholderTextColor="#9ca3af"
          />
        </View>
      </View>

      <Text style={styles.label}>Notes</Text>
      <TextInput
        style={[styles.input, { height: 80, textAlignVertical: "top" }]}
        value={form.notes}
        onChangeText={(v) => updateForm("notes", v)}
        placeholder="Any additional notes..."
        placeholderTextColor="#9ca3af"
        multiline
      />

      <View style={styles.actions}>
        <TouchableOpacity
          style={[styles.submitButton, saving && styles.buttonDisabled]}
          onPress={handleSubmit}
          disabled={saving}
        >
          {saving ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.submitText}>
              {isEditing ? "Update Case" : "Add Case"}
            </Text>
          )}
        </TouchableOpacity>
        <TouchableOpacity
          style={styles.cancelButton}
          onPress={() => navigation.goBack()}
        >
          <Text style={styles.cancelText}>Cancel</Text>
        </TouchableOpacity>
      </View>

      <View style={{ height: 40 }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f9fafb", padding: 20 },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  title: { fontSize: 22, fontWeight: "700", color: "#18181b" },
  subtitle: { fontSize: 14, color: "#6b7280", marginTop: 4, marginBottom: 16 },
  sectionTitle: {
    fontSize: 16,
    fontWeight: "600",
    color: "#18181b",
    marginTop: 20,
    marginBottom: 4,
  },
  label: {
    fontSize: 14,
    fontWeight: "500",
    color: "#374151",
    marginBottom: 6,
    marginTop: 12,
  },
  input: {
    borderWidth: 1,
    borderColor: "#d1d5db",
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    color: "#18181b",
    backgroundColor: "#fff",
  },
  row: { flexDirection: "row", gap: 12 },
  flex1: { flex: 1 },
  picker: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#d1d5db",
    borderRadius: 8,
    padding: 12,
    backgroundColor: "#fff",
  },
  pickerText: { fontSize: 16, color: "#18181b" },
  pickerOptions: {
    borderWidth: 1,
    borderColor: "#d1d5db",
    borderRadius: 8,
    marginTop: 4,
    backgroundColor: "#fff",
    overflow: "hidden",
  },
  pickerOptionsScroll: {
    borderWidth: 1,
    borderColor: "#d1d5db",
    borderRadius: 8,
    marginTop: 4,
    backgroundColor: "#fff",
    maxHeight: 200,
  },
  pickerOption: { padding: 12, borderBottomWidth: 1, borderBottomColor: "#f3f4f6" },
  pickerOptionSelected: { backgroundColor: "#f3f4f6" },
  pickerOptionText: { fontSize: 15, color: "#374151" },
  pickerOptionTextSelected: { fontWeight: "600", color: "#18181b" },
  actions: { marginTop: 24, gap: 10 },
  submitButton: {
    backgroundColor: "#18181b",
    borderRadius: 8,
    padding: 14,
    alignItems: "center",
  },
  buttonDisabled: { opacity: 0.6 },
  submitText: { color: "#fff", fontSize: 16, fontWeight: "600" },
  cancelButton: {
    borderRadius: 8,
    padding: 14,
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#d1d5db",
  },
  cancelText: { color: "#6b7280", fontSize: 16 },
  priorityPickerContent: { flexDirection: "row", alignItems: "center", gap: 6 },
  priorityDescription: { fontSize: 12, color: "#9ca3af", marginTop: 2 },
  searchButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    backgroundColor: "#3b82f6",
    borderRadius: 8,
    padding: 12,
    marginTop: 16,
  },
  searchButtonText: { color: "#fff", fontSize: 15, fontWeight: "600" },
  searchHint: {
    fontSize: 12,
    color: "#9ca3af",
    textAlign: "center",
    marginTop: 6,
    marginBottom: 4,
  },
  backButton: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginBottom: 16,
  },
  backButtonText: { fontSize: 15, color: "#18181b", fontWeight: "500" },
  noResults: {
    alignItems: "center",
    paddingVertical: 40,
  },
  noResultsTitle: { fontSize: 18, fontWeight: "600", color: "#18181b", marginTop: 12 },
  noResultsText: { fontSize: 14, color: "#6b7280", textAlign: "center", marginTop: 8, paddingHorizontal: 20 },
  resultCard: {
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 2,
    borderColor: "#e5e7eb",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 4,
    elevation: 1,
  },
  resultCardSelected: {
    borderColor: "#10b981",
    backgroundColor: "#f0fdf4",
  },
  resultHeader: { marginBottom: 8 },
  resultBadgeRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  resultIndexBadge: {
    backgroundColor: "#18181b",
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 6,
  },
  resultIndexText: { color: "#fff", fontSize: 14, fontWeight: "700" },
  resultParties: {
    fontSize: 15,
    fontWeight: "600",
    color: "#18181b",
    marginBottom: 8,
  },
  resultDetails: { gap: 4 },
  resultDetailRow: {
    flexDirection: "row",
    gap: 6,
  },
  resultDetailLabel: { fontSize: 13, color: "#6b7280", fontWeight: "500" },
  resultDetailValue: { fontSize: 13, color: "#18181b" },
  lastActionBox: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 6,
    backgroundColor: "#f3f4f6",
    borderRadius: 8,
    padding: 10,
    marginTop: 10,
  },
  lastActionText: { fontSize: 13, color: "#374151", flex: 1 },
  selectedHint: {
    fontSize: 13,
    color: "#10b981",
    fontWeight: "500",
    marginTop: 10,
    textAlign: "center",
  },
  verifyActions: { gap: 10, marginTop: 8 },
  verifyButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    backgroundColor: "#10b981",
    borderRadius: 8,
    padding: 14,
  },
  verifyButtonText: { color: "#fff", fontSize: 16, fontWeight: "600" },
  manualButton: {
    borderRadius: 8,
    padding: 14,
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#d1d5db",
    backgroundColor: "#fff",
  },
  manualButtonText: { color: "#374151", fontSize: 15, fontWeight: "500" },
  captchaContainer: {
    backgroundColor: "#fffbeb",
    borderWidth: 1,
    borderColor: "#fcd34d",
    borderRadius: 12,
    padding: 16,
    marginTop: 12,
  },
  captchaHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginBottom: 8,
  },
  captchaTitle: {
    fontSize: 15,
    fontWeight: "600",
    color: "#92400e",
  },
  captchaSubtitle: {
    fontSize: 13,
    color: "#78716c",
    marginBottom: 12,
  },
  openWebCivilButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    backgroundColor: "#2563eb",
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
  },
  openWebCivilButtonText: {
    color: "#fff",
    fontSize: 15,
    fontWeight: "600",
  },
  captchaSteps: {
    backgroundColor: "#fef3c7",
    borderRadius: 8,
    padding: 12,
    gap: 6,
    marginBottom: 12,
  },
  captchaStepText: {
    fontSize: 13,
    color: "#78716c",
  },
  dismissCaptchaButton: {
    alignItems: "center",
    padding: 10,
  },
  dismissCaptchaText: {
    fontSize: 14,
    color: "#92400e",
    fontWeight: "500",
    textDecorationLine: "underline",
  },
});
