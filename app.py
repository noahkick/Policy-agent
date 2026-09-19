import sys
from datetime import date
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))
from agent.graph import run_agent
from agent.ingestion import load_policy_documents
from agent.policy_store import PolicyStore

# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Policy Intelligence",
    page_icon="◇",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================================================
# SESSION STATE
# =========================================================

if "history" not in st.session_state:
    st.session_state.history = []


# =========================================================
# POLICY DATA
# =========================================================

POLICY_DOCUMENTS = load_policy_documents(Path(__file__).parent / "data" / "policies")
POLICY_STORE = PolicyStore()
POLICY_STORE.add_documents(POLICY_DOCUMENTS)

_VENDOR_ALIASES = {"Vendor X": "Vendor-X", "Vendor Y": "Vendor-Y"}


# =========================================================
# CSS
# =========================================================

st.markdown("""
<style>

.stApp {
    background:
        radial-gradient(circle at 82% 10%, rgba(80,85,255,.20), transparent 25%),
        radial-gradient(circle at 12% 70%, rgba(0,160,255,.08), transparent 25%),
        radial-gradient(circle at 90% 90%, rgba(145,65,255,.12), transparent 25%),
        #05050b;
    color:#f5f5ff;
}

/* animated glow */

.stApp::before {
    content:"";
    position:fixed;
    width:600px;
    height:600px;
    right:-180px;
    top:80px;
    border-radius:50%;
    background:
        radial-gradient(
            circle,
            rgba(78,90,255,.20),
            transparent 68%
        );
    filter:blur(25px);
    animation:floatGlow 9s ease-in-out infinite alternate;
    pointer-events:none;
}

@keyframes floatGlow {
    from {
        transform:translate(0,0) scale(1);
    }
    to {
        transform:translate(-110px,70px) scale(1.18);
    }
}

/* stars */

.stApp::after {
    content:"";
    position:fixed;
    inset:0;
    background-image:
        radial-gradient(circle,rgba(255,255,255,.25) 1px,transparent 1px),
        radial-gradient(circle,rgba(110,120,255,.15) 1px,transparent 1px);
    background-size:110px 110px,170px 170px;
    opacity:.15;
    animation:moveStars 22s linear infinite;
    pointer-events:none;
}

@keyframes moveStars {
    from {
        background-position:0 0,40px 60px;
    }
    to {
        background-position:110px 110px,-130px 190px;
    }
}

/* layout */

.block-container {
    max-width:1400px;
    padding-top:25px;
    padding-bottom:100px;
}

/* =========================================================
SIDEBAR
========================================================= */

[data-testid="stSidebar"] {
    background:#07070f;
    border-right:1px solid rgba(255,255,255,.07);
}

[data-testid="stSidebar"] > div:first-child {
    padding:30px 18px;
}

[data-testid="stSidebar"] [data-testid="stRadio"] label {
    padding:12px 14px !important;
    border-radius:13px;
    color:#85869b !important;
}

[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
    background:rgba(100,100,255,.08);
    color:#fff !important;
}

/* =========================================================
TEXT
========================================================= */

.small-label {
    color:#7d7aff;
    font-size:10px;
    font-weight:700;
    letter-spacing:3px;
    margin-bottom:12px;
}

.hero-title {
    font-size:58px;
    line-height:1.03;
    font-weight:800;
    letter-spacing:-3px;
    background:linear-gradient(
        110deg,
        #ffffff,
        #c2c4ff,
        #73d8ff
    );
    -webkit-background-clip:text;
    -webkit-text-fill-color:transparent;
}

.hero-sub {
    color:#85869b;
    font-size:14px;
    line-height:1.8;
    max-width:540px;
}

.section-title {
    font-size:28px;
    font-weight:700;
    letter-spacing:-1px;
}

.section-sub {
    color:#73758a;
    font-size:12px;
}

/* =========================================================
CARDS
========================================================= */

[data-testid="stVerticalBlockBorderWrapper"] {
    background:rgba(255,255,255,.025);
    border:1px solid rgba(255,255,255,.07);
    border-radius:20px;
}

/* =========================================================
SELECT BOXES
========================================================= */

[data-baseweb="select"] > div {
    background:rgba(5,6,14,.90) !important;
    border:1px solid rgba(255,255,255,.09) !important;
    border-radius:12px !important;
}

[data-baseweb="select"] span {
    color:#e8e9f1 !important;
}

/* DATE */

input {
    background:rgba(5,6,14,.9) !important;
    color:white !important;
    border-radius:12px !important;
}

/* =========================================================
BUTTON
========================================================= */

.stButton > button {
    height:50px;
    border:none !important;
    border-radius:14px !important;

    background:
        linear-gradient(
            100deg,
            #7165ff,
            #398eff
        ) !important;

    color:white !important;
    font-weight:700 !important;

    box-shadow:
        0 15px 40px rgba(76,80,255,.25);

    transition:.25s ease;
}

.stButton > button:hover {
    transform:translateY(-2px);
    box-shadow:
        0 20px 50px rgba(76,80,255,.4);
}

/* =========================================================
HISTORY
========================================================= */

.history-question {
    font-size:15px;
    font-weight:600;
    color:#eeeeF7;
}

.history-output {
    color:#9a9bad;
    font-size:12px;
    line-height:1.7;
}

.history-time {
    color:#606276;
    font-size:10px;
}

/* =========================================================
STATUS
========================================================= */

.status {
    padding:7px 12px;
    border-radius:30px;
    background:rgba(90,90,255,.08);
    border:1px solid rgba(100,100,255,.12);
    color:#9698b0;
    font-size:10px;
}

/* =========================================================
REMOVE DEFAULT
========================================================= */

#MainMenu {
    visibility:hidden;
}

footer {
    visibility:hidden;
}

header {
    background:transparent !important;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.markdown(
        "<div style='font-size:35px;color:#7775ff;'>◇</div>",
        unsafe_allow_html=True
    )

    st.markdown("### Policy Intelligence")

    st.caption("REASONING ENGINE")

    st.divider()

    page = st.radio(
        "WORKSPACE",
        [
            "⌂  Overview",
            "◇  Ask Policy",
            "▣  Policy Library",
            "◷  Analysis History"
        ],
        label_visibility="visible"
    )

    st.divider()

    st.caption("SYSTEM")

    st.success("Policy Engine Ready")


# =========================================================
# EMPTY ASK POLICY PAGE
# =========================================================

if page == "◇  Ask Policy":

    st.markdown(
        "<div class='small-label'>WORKSPACE</div>",
        unsafe_allow_html=True
    )

    st.title("Ask Policy")

    st.caption(
        "This workspace is ready for the policy investigation module."
    )

    st.info(
        "Policy questions are currently generated from the investigation "
        "context on the Overview page."
    )

    st.stop()


# =========================================================
# POLICY LIBRARY (backed by the real bundled dataset)
# =========================================================

if page == "▣  Policy Library":

    st.markdown(
        "<div class='small-label'>KNOWLEDGE BASE</div>",
        unsafe_allow_html=True
    )

    st.title("Policy Library")

    st.caption(
        f"{len(POLICY_DOCUMENTS)} policy document chunk(s) currently loaded."
    )

    for policy in POLICY_DOCUMENTS:
        metadata = policy.get("metadata", {})
        title = metadata.get("title") or metadata.get("source", "Policy document")
        with st.container(border=True):
            st.markdown(f"**{title}**")
            st.caption(
                f"Source {metadata.get('source', 'unknown')} · "
                f"section={metadata.get('section', 'unknown')}"
            )
            st.write(policy["content"])

    st.stop()


# =========================================================
# ANALYSIS HISTORY
# =========================================================

if page == "◷  Analysis History":

    st.markdown(
        "<div class='small-label'>INVESTIGATION RECORD</div>",
        unsafe_allow_html=True
    )

    st.title("Analysis History")

    st.caption(
        "Questions investigated during this session."
    )

    st.markdown("<br>", unsafe_allow_html=True)

    if not st.session_state.history:

        with st.container(border=True):

            st.markdown("### ◇ No investigations yet")

            st.caption(
                "Your analyzed policy questions will appear here."
            )

    else:

        st.markdown(
            f"**{len(st.session_state.history)} investigation(s)**"
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # newest first
        for i, item in enumerate(
            reversed(st.session_state.history)
        ):

            with st.container(border=True):

                st.markdown(
                    f"### {item['question']}"
                )

                st.caption(
                    f"Analyzed on {item['time']}"
                )

                st.markdown("---")

                if item["status"] == "NOT PERMITTED":

                    st.error(
                        f"**{item['status']}**"
                    )

                elif item["status"].startswith("RETENTION PERIOD"):

                    st.warning(
                        f"**{item['status']}**"
                    )

                elif item["status"] == "ADDITIONAL CONTEXT REQUIRED":

                    st.warning(
                        f"**{item['status']}**"
                    )

                elif item["status"] == "PERMITTED":

                    st.success(
                        f"**{item['status']}**"
                    )

                elif item["status"] == "CONFLICT DETECTED":

                    st.error(
                        f"**{item['status']}**"
                    )

                else:

                    st.info(
                        f"**{item['status']}**"
                    )

                st.markdown(
                    f"**Output:** {item['output']}"
                )

                st.caption(
                    " · ".join(item["context"])
                )

                if item["policies"]:

                    st.markdown(
                        "**Policies:** "
                        + " · ".join(item["policies"])
                    )

    st.stop()


# =========================================================
# OVERVIEW
# =========================================================

st.caption("POLICY INTELLIGENCE PLATFORM")

top1, top2 = st.columns([7,1])

with top1:

    st.markdown(
        "<div class='status'>● REASONING SYSTEM ONLINE</div>",
        unsafe_allow_html=True
    )

with top2:

    st.caption("v1.0")


# =========================================================
# HERO
# =========================================================

st.markdown("<br>", unsafe_allow_html=True)

hero_left, hero_right = st.columns([1.25,.75])

with hero_left:

    st.markdown(
        "<div class='small-label'>POLICY INTELLIGENCE</div>",
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="hero-title">
        KNOW THE RULE.<br>
        UNDERSTAND THE<br>
        CONTEXT.
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="hero-sub">
        A reasoning-driven policy agent that connects
        questions with the rules, versions, scope and
        exceptions that actually apply.
        </div>
        """,
        unsafe_allow_html=True
    )


with hero_right:

    st.markdown("<br><br>", unsafe_allow_html=True)

    st.markdown(
        """
        <div style="
            width:280px;
            height:280px;
            margin:auto;
            border-radius:50%;
            background:
            radial-gradient(
                circle at 40% 35%,
                rgba(170,170,255,.80),
                rgba(70,90,255,.38) 24%,
                rgba(30,40,130,.12) 48%,
                transparent 70%
            );
            box-shadow:
            0 0 110px rgba(70,80,255,.35);
        ">
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================================================
# INVESTIGATION
# =========================================================

st.markdown("<br><br><br>", unsafe_allow_html=True)

st.markdown(
    "<div class='small-label'>INVESTIGATION</div>",
    unsafe_allow_html=True
)

st.markdown(
    "<div class='section-title'>Build the policy context</div>",
    unsafe_allow_html=True
)

st.markdown(
    "<div class='section-sub'>Select the facts that define your policy question.</div>",
    unsafe_allow_html=True
)

st.markdown("<br>", unsafe_allow_html=True)


# =========================================================
# CONTEXT
# =========================================================

c1, c2, c3 = st.columns(3)

with c1:

    region = st.selectbox(
        "Region",
        [
            "Select region",
            "Not applicable",
            "India",
            "EU",
            "US",
            "UK",
            "APAC"
        ]
    )

    department = st.selectbox(
        "Department",
        [
            "Select department",
            "Not applicable",
            "Analytics",
            "Support",
            "Engineering",
            "Finance",
            "HR",
            "Marketing"
        ]
    )

    action = st.selectbox(
        "Action",
        [
            "Select action",
            "Not applicable",
            "Access",
            "Share",
            "Retain",
        ]
    )


with c2:

    role = st.selectbox(
        "Role",
        [
            "Select role",
            "Not applicable",
            "Employee",
            "Manager",
            "Analyst",
            "Administrator",
            "Data Scientist"
        ]
    )

    dataset = st.selectbox(
        "Dataset / Data Type",
        [
            "Select dataset",
            "Not applicable",
            "Dataset Y",
            "Customer Data",
            "Employee Data",
            "Financial Data",
            "Public Data"
        ]
    )

    if action == "Access":
        device = st.selectbox(
            "Device",
            ["Select device", "Not applicable", "Corporate laptop", "Personal laptop"],
        )
        mfa = st.selectbox(
            "MFA",
            ["Select MFA status", "Not applicable", "Active", "Inactive"],
        )
        purpose = st.selectbox(
            "Purpose",
            [
                "Select purpose",
                "Not applicable",
                "Reporting",
                "Investigation",
                "Active customer case",
            ],
        )
        required_for_assigned_work = st.selectbox(
            "Required for assigned work",
            ["Select requirement", "Not applicable", "Yes", "No"],
        )
    else:
        device = "Not applicable"
        mfa = "Not applicable"
        purpose = "Not applicable"
        required_for_assigned_work = "Not applicable"


with c3:

    vendor = st.selectbox(
        "Vendor",
        [
            "Select vendor",
            "Not applicable",
            "Vendor X",
            "Vendor Y",
            "Approved Vendor",
            "External Vendor"
        ]
    )

    policy_date = st.date_input(
        "Policy Date",
        value=date.today()
    )


# =========================================================
# AUTOMATIC QUESTION
# =========================================================

_PLACEHOLDER_VALUES = {
    "Select region",
    "Select department",
    "Select role",
    "Select dataset",
    "Select vendor",
    "Select action",
    "Select device",
    "Select MFA status",
    "Select purpose",
    "Select requirement",
}
_NOT_APPLICABLE = "Not applicable"
_CONTEXT_FIELDS = {
    "Region": region,
    "Department": department,
    "Role": role,
    "Dataset / Data Type": dataset,
    "Vendor": vendor,
    "Action": action,
}
if action == "Access":
    _CONTEXT_FIELDS.update(
        {
            "Device": device,
            "MFA": mfa,
            "Purpose": purpose,
            "Required for assigned work": required_for_assigned_work,
        }
    )
provided_context = {
    label: value
    for label, value in _CONTEXT_FIELDS.items()
    if value not in _PLACEHOLDER_VALUES and value != _NOT_APPLICABLE
}
missing_context = [
    label
    for label, value in _CONTEXT_FIELDS.items()
    if value in _PLACEHOLDER_VALUES or (label == "Action" and value == _NOT_APPLICABLE)
]
not_applicable_context = [
    label for label, value in _CONTEXT_FIELDS.items() if value == _NOT_APPLICABLE
]


def _question_fragment(label: str, value: str) -> str:
    fragments = {
        "Region": f"in {value}",
        "Department": f"for the {value} department",
        "Role": f"for a {value}",
        "Dataset / Data Type": f"about {value}",
        "Vendor": f"with {value}",
        "Action": value.casefold(),
    }
    return fragments[label]


def _display_context_label(value: str) -> str:
    labels = {
        "region": "Region",
        "department": "Department",
        "role": "Role",
        "dataset": "Dataset / Data Type",
        "vendor": "Vendor",
        "action": "Action",
        "resource": "Resource",
        "device": "Device",
        "mfa": "MFA",
        "business_purpose": "Purpose",
        "required_for_assigned_work": "Required for assigned work",
        "required_approval": "Required approval",
        "retention_period": "Retention period",
    }
    return labels.get(value, value.replace("_", " ").capitalize())


def _context_value(label: str, value: str) -> object:
    if label == "Action":
        return value.casefold()
    if label == "Vendor":
        return _VENDOR_ALIASES.get(value, value)
    if label == "Device":
        return value.casefold()
    if label == "MFA":
        return value.casefold() == "active"
    if label == "Purpose":
        return {
            "Reporting": "reporting and investigation work",
            "Investigation": "reporting and investigation work",
            "Active customer case": "active customer case",
        }.get(value, value.casefold())
    if label == "Required for assigned work":
        return value == "Yes"
    return value


def _situation_from_context(context: dict[str, str], policy_date: date) -> dict[str, object]:
    context_keys = {
        "Region": "region",
        "Department": "department",
        "Role": "role",
        "Dataset / Data Type": "resource",
        "Vendor": "vendor",
        "Action": "action",
        "Device": "device",
        "MFA": "mfa",
        "Purpose": "business_purpose",
        "Required for assigned work": "required_for_assigned_work",
    }
    situation = {
        context_keys[label]: _context_value(label, value)
        for label, value in context.items()
    }
    situation["policy_date"] = policy_date.isoformat()
    return situation


def _rule_evidence_for_display(
    rules: object, action: object, resource: object
) -> list[dict[str, object]]:
    if not isinstance(rules, list):
        return []
    evidence: list[dict[str, object]] = []
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        if str(rule.get("action", "")).casefold() != str(action).casefold():
            continue
        if str(rule.get("resource", "")).casefold() != str(resource).casefold():
            continue
        items = rule.get("evidence", [])
        if isinstance(items, list):
            evidence.extend(item for item in items if isinstance(item, dict))
    return evidence


def _compose_display_output(output: str, evidence: list[dict[str, object]]) -> str:
    """Compose truthful UI text after adding relevant validated-rule evidence."""

    if not evidence:
        return output

    output = output.replace("\n\nNo supporting policy evidence was available.", "")
    output = output.replace(
        "No policy rule applies to the supplied situation.",
        "Relevant policy rules were evaluated, but the supplied facts do not satisfy a permission rule.",
    )
    if "Supporting evidence:" in output:
        return output

    evidence_lines = [
        f"- {item['excerpt']} ({item.get('source', 'policy source')})"
        for item in evidence
        if isinstance(item.get("excerpt"), str)
    ]
    if not evidence_lines:
        return output
    return output + "\n\nSupporting evidence:\n" + "\n".join(evidence_lines)


def _build_generated_question(context: dict[str, str]) -> str:
    action_value = context.get("Action")
    if not action_value:
        return "Which policy action applies to this request?"

    action_text = action_value.casefold()
    actor = (
        f"the {context['Department']} department"
        if "Department" in context
        else f"a {context['Role']}"
        if "Role" in context
        else "the requester"
    )
    subject = context.get("Dataset / Data Type")
    region_text = (
        f" in {context['Region']}" if "Region" in context else ""
    )
    if action_text == "share" and subject and "Vendor" in context:
        return f"Can {actor} share {subject} with {context['Vendor']}{region_text}?"
    elif action_text == "access" and subject:
        return f"Can {actor} access {subject}{region_text}?"
    elif action_text == "retain" and subject:
        return f"Can {actor} retain {subject}{region_text}?"
    return f"Can {actor} {action_text} this request{region_text}?"


generated_question = _build_generated_question(provided_context)

st.markdown("<br>", unsafe_allow_html=True)

with st.container(border=True):

    st.markdown(
        "<div class='small-label'>GENERATED QUESTION</div>",
        unsafe_allow_html=True
    )

    st.markdown(f"### {generated_question}")
    st.caption(
        "Generated from the context provided; the policy engine identifies any additional requirements."
    )

st.caption(
    "Provided: " + (", ".join(provided_context) if provided_context else "None")
)
st.caption(
    "Missing: " + (", ".join(missing_context) if missing_context else "None")
)
st.caption(
    "Not applicable: "
    + (", ".join(not_applicable_context) if not_applicable_context else "None")
)

st.markdown("<br>", unsafe_allow_html=True)

st.info(
    "Provide the context relevant to your question. Missing information will be identified by the policy engine when required."
)

analyze = st.button(
    "ANALYZE POLICY  →",
    use_container_width=True
)


# =========================================================
# ANALYSIS - run the complete retrieval, extraction, validation, and
# deterministic evaluation workflow.
# =========================================================

if analyze:

    situation = _situation_from_context(provided_context, policy_date)

    agent_state = run_agent(
        {
            "query": generated_question,
            "execution_metadata": {"situation": situation},
        },
        vector_store=POLICY_STORE,
    )
    raw_result = agent_state.get("policy_evaluation_result", {})
    result = raw_result if isinstance(raw_result, dict) else {}
    decision = agent_state.get("decision", "UNKNOWN")

    status_map = {
        "DENY": "NOT PERMITTED",
        "ALLOW": "PERMITTED",
        "CONDITIONAL": "CONDITIONAL",
        "CONFLICT": "CONFLICT DETECTED",
        "UNKNOWN": "ADDITIONAL CONTEXT REQUIRED",
    }
    status = status_map.get(decision, decision)

    output = agent_state.get("final_answer") or result.get("reason", "")
    policies = []
    evidence = result.get("evidence", agent_state.get("supporting_excerpts", []))
    if not evidence:
        evidence = _rule_evidence_for_display(
            agent_state.get("extracted_policies"),
            situation.get("action"),
            situation.get("resource"),
        )
    output = _compose_display_output(output, evidence)
    if isinstance(evidence, list):
        for item in evidence:
            if not isinstance(item, dict):
                continue
            metadata = item.get("metadata", {})
            source = item.get("source")
            if not source and isinstance(metadata, dict):
                source = metadata.get("source") or metadata.get("title")
            if isinstance(source, str) and source not in policies:
                policies.append(source)
    if not policies and result.get("applicable_rules"):
        policies.append(f"{len(result['applicable_rules'])} evaluated rule(s)")
    decision_missing_context = result.get("missing_context", [])

    # =====================================================
    # SAVE HISTORY
    # =====================================================

    history_item = {
        "question": generated_question,
        "status": status,
        "output": output,
        "policies": policies,
        "time": date.today().strftime("%d %b %Y"),
        "context": [
            f"Region: {region}",
            f"Department: {department}",
            f"Role: {role}",
            f"Dataset: {dataset}",
            f"Vendor: {vendor}",
            f"Date: {policy_date}"
        ]
    }

    st.session_state.history.append(history_item)


    # =====================================================
    # RESULT
    # =====================================================

    st.markdown("<br><br>", unsafe_allow_html=True)

    st.markdown(
        "<div class='small-label'>REASONING RESULT</div>",
        unsafe_allow_html=True
    )

    st.markdown(
        "<div class='section-title'>The rule that applies</div>",
        unsafe_allow_html=True
    )

    st.markdown("<br>", unsafe_allow_html=True)


    # RESULT STATUS

    if status == "NOT PERMITTED":

        st.error(f"### {status}")

    elif status.startswith("RETENTION PERIOD"):

        st.warning(f"### {status}")

    elif status == "ADDITIONAL CONTEXT REQUIRED":

        st.warning(f"### {status}")

    elif status == "PERMITTED":

        st.success(f"### {status}")

    elif status == "CONFLICT DETECTED":

        st.error(f"### {status}")

    else:

        st.info(f"### {status}")


    # OUTPUT

    with st.container(border=True):

        st.markdown("### Why")

        st.write(output)

        if decision_missing_context:
            st.markdown("**Additional information required:**")
            st.caption(
                "• "
                + "\n• ".join(_display_context_label(value) for value in decision_missing_context)
            )


    # POLICIES

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("### Applicable policies")

    if policies:

        pcols = st.columns(len(policies))

        for col, policy in zip(pcols, policies):

            with col:

                with st.container(border=True):

                    st.markdown(f"**{policy}**")

                    st.caption(
                        "Matched during policy reasoning."
                    )
    else:
        st.caption("No evaluated policy rule matched the supplied facts.")


    # REASONING TRACE

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("### Reasoning trace")

    reasoning_steps = [
        f"Question understood: {generated_question}",
        f"Context resolved: {region} · {department} · {role}",
        f"Data identified: {dataset}",
        f"Vendor identified: {vendor}",
        f"Policy date checked: {policy_date}",
        "Currently effective policy versions resolved (superseded/future-dated versions excluded)",
        "Scope specificity evaluated - most specific matching policy selected",
        f"Result: {status}",
    ]

    for i, step in enumerate(reasoning_steps, 1):

        with st.container(border=True):

            a, b = st.columns([.6, 9])

            with a:
                st.markdown(f"**{i:02d}**")

            with b:
                st.write(step)


# =========================================================
# FOOTER
# =========================================================

st.markdown("<br><br>", unsafe_allow_html=True)

st.divider()

st.caption(
    "POLICY INTELLIGENCE  ·  UNDERSTAND THE CONTEXT · RESOLVE THE RULE"
)
