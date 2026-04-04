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
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { casesApi } from "../services/api";

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

export default function CaseFormScreen({ route, navigation }: any) {
  const editId = route.params?.id;
  const isEditing = !!editId;

  const [form, setForm] = useState({
    court_type: "supreme",
    county: "",
    index_number: "",
    case_year: "",
    case_status: "active",
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
});
