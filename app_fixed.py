import streamlit as st
from datetime import date

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
# BACKEND INTEGRATION
# =========================================================

from pathlib import Path

try:
    from agent.graph import run_agent
    from agent.ingestion import load_policy_documents
    from agent.policy_store import PolicyStore
    BACKEND_AVAILABLE = True
    BACKEND_ERROR = None
except Exception as exc:
    BACKEND_AVAILABLE = False
    BACKEND_ERROR = exc


POLICY_DIR = Path(__file__).resolve().parent / "data" / "policies"


@st.cache_resource(show_spinner=False)
def build_policy_store():
    """Load policy documents once and build the local search index."""
    store = PolicyStore()

    if not POLICY_DIR.exists():
        return store, 0

    chunks = load_policy_documents(POLICY_DIR)
    store.add_documents(chunks)
    return store, len(chunks)


def context_to_situation(region, department, role, dataset, vendor, policy_date):
    """Convert UI context into explicit facts for the policy engine."""
    return {
        "region": region,
        "department": department,
        "role": role,
        "resource": dataset,
        "dataset": dataset,
        "vendor": vendor,
        "policy_date": str(policy_date),
    }


def display_status(status):
    """Render a consistent status message."""
    if status == "DENY":
        st.error("### DENY")
    elif status == "CONDITIONAL":
        st.warning("### CONDITIONAL")
    elif status == "CONFLICT":
        st.warning("### CONFLICT")
    elif status == "UNKNOWN":
        st.info("### UNKNOWN")
    elif status == "ALLOW":
        st.success("### ALLOW")
    else:
        st.info(f"### {status}")




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

    if BACKEND_AVAILABLE:
        st.success("Policy Engine Ready")
    else:
        st.error("Policy Backend Unavailable")


# =========================================================
# EMPTY POLICY LIBRARY
# =========================================================

if page == "▣  Policy Library":

    st.markdown(
        "<div class='small-label'>KNOWLEDGE BASE</div>",
        unsafe_allow_html=True
    )

    st.title("Policy Library")

    st.caption(
        "Your policy documents and metadata will appear here."
    )

    st.info(
        "Policy ingestion and document browsing will be connected here."
    )

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

                elif item["status"] == "RETENTION PERIOD: 2 YEARS":

                    st.warning(
                        f"**{item['status']}**"
                    )

                elif item["status"] == "ADDITIONAL CONTEXT REQUIRED":

                    st.warning(
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
            "Analytics",
            "Support",
            "Engineering",
            "Finance",
            "HR",
            "Marketing"
        ]
    )


with c2:

    role = st.selectbox(
        "Role",
        [
            "Select role",
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
            "Dataset Y",
            "Customer Data",
            "Employee Data",
            "Financial Data",
            "Public Data"
        ]
    )


with c3:

    vendor = st.selectbox(
        "Vendor",
        [
            "Select vendor",
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

all_selected = (
    region != "Select region"
    and department != "Select department"
    and role != "Select role"
    and dataset != "Select dataset"
    and vendor != "Select vendor"
)


if all_selected:

    if dataset in ["Dataset Y", "Customer Data"]:

        generated_question = (
            f"Can the {department} team share "
            f"{dataset} with {vendor} in {region} "
            f"on {policy_date}?"
        )

    else:

        generated_question = (
            f"Can a {role} from {department} use or share "
            f"{dataset} with {vendor} in {region} "
            f"on {policy_date}?"
        )

    st.markdown("<br>", unsafe_allow_html=True)

    with st.container(border=True):

        st.markdown(
            "<div class='small-label'>GENERATED QUESTION</div>",
            unsafe_allow_html=True
        )

        st.markdown(
            f"### {generated_question}"
        )

        st.caption(
            "Generated automatically from the selected context."
        )

    st.markdown("<br>", unsafe_allow_html=True)

    analyze = st.button(
        "ANALYZE POLICY  →",
        use_container_width=True
    )

else:

    st.markdown("<br>", unsafe_allow_html=True)

    st.info(
        "Complete the context above to generate the policy question automatically."
    )

    analyze = False


# =========================================================
# ANALYSIS
# =========================================================

if analyze:

    if not BACKEND_AVAILABLE:
        st.error("The policy backend could not be loaded.")
        st.exception(BACKEND_ERROR)
        st.stop()

    if not POLICY_DIR.exists():
        st.error(f"Policy directory not found: `{POLICY_DIR}`")
        st.info("Create data/policies/ and add the policy documents before running an analysis.")
        st.stop()

    try:
        policy_store, chunk_count = build_policy_store()

        if chunk_count == 0:
            st.warning("No policy documents were loaded.")
            st.stop()

        situation = context_to_situation(
            region,
            department,
            role,
            dataset,
            vendor,
            policy_date,
        )

        with st.spinner("Retrieving and evaluating applicable policies..."):
            result = run_agent(
                {
                    "query": generated_question,
                    "execution_metadata": {
                        "situation": situation,
                    },
                },
                vector_store=policy_store,
                top_k=5,
            )

        status = result.get("decision", "UNKNOWN")
        output = result.get(
            "final_answer",
            "The system could not produce a final answer.",
        )

        # Save the actual backend result rather than a hard-coded scenario.
        evidence = result.get("evidence", [])
        conflicts = result.get("conflicts", [])
        retrieved = result.get("relevant_chunks", [])

        policies = []
        for chunk in retrieved:
            metadata = chunk.get("metadata", {})
            source = metadata.get("source") or chunk.get("document_name")
            if source and source not in policies:
                policies.append(source)

        if not policies:
            policies = ["No supporting policy document identified"]

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
                f"Date: {policy_date}",
            ],
        }

        st.session_state.history.append(history_item)

        # =====================================================
        # RESULT
        # =====================================================

        st.markdown("<br><br>", unsafe_allow_html=True)

        st.markdown(
            "<div class='small-label'>REASONING RESULT</div>",
            unsafe_allow_html=True,
        )

        st.markdown(
            "<div class='section-title'>The rule that applies</div>",
            unsafe_allow_html=True,
        )

        st.markdown("<br>", unsafe_allow_html=True)

        display_status(status)

        with st.container(border=True):
            st.markdown("### Why")
            st.write(output)

        # =====================================================
        # EVIDENCE
        # =====================================================

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### Evidence")

        if evidence:
            for item in evidence:
                if not isinstance(item, dict):
                    st.write(item)
                    continue

                metadata = item.get("metadata", {})
                source = metadata.get("source", "Unknown source")
                section = metadata.get("section")
                page = metadata.get("page")
                content = item.get("content") or item.get("excerpt") or ""

                label = source
                if section:
                    label += f" · {section}"
                if page:
                    label += f" · page {page}"

                with st.container(border=True):
                    st.markdown(f"**{label}**")
                    if content:
                        st.write(content)
        else:
            st.caption("No supporting policy evidence was returned.")

        # =====================================================
        # APPLICABLE POLICIES
        # =====================================================

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### Retrieved policies")

        pcols = st.columns(max(1, min(len(policies), 3)))

        for index, policy in enumerate(policies):
            with pcols[index % len(pcols)]:
                with st.container(border=True):
                    st.markdown(f"**{policy}**")
                    st.caption("Retrieved during policy analysis.")

        # =====================================================
        # CONFLICTS / WARNINGS
        # =====================================================

        if conflicts:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("### Policy conflicts")

            for conflict in conflicts:
                with st.container(border=True):
                    st.write(conflict)

        warnings = result.get("warnings", [])
        errors = result.get("errors", [])

        if warnings:
            with st.expander("Warnings"):
                for warning in warnings:
                    st.warning(warning)

        if errors:
            with st.expander("Execution errors"):
                for error in errors:
                    st.error(error)

        # =====================================================
        # REASONING TRACE
        # =====================================================

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### Reasoning trace")

        reasoning_steps = [
            f"Question received: {generated_question}",
            f"Context supplied: {region} · {department} · {role}",
            f"Data identified: {dataset}",
            f"Vendor identified: {vendor}",
            f"Policy date supplied: {policy_date}",
            f"Retrieved {len(retrieved)} relevant policy chunk(s)",
            "Applicable structured rules evaluated",
            f"Policy engine returned: {status}",
            "Final response generated from the available policy result and evidence",
        ]

        for i, step in enumerate(reasoning_steps, 1):
            with st.container(border=True):
                a, b = st.columns([0.6, 9])

                with a:
                    st.markdown(f"**{i:02d}**")

                with b:
                    st.write(step)

    except Exception as exc:
        st.error("Policy analysis failed safely.")
        st.exception(exc)



# =========================================================
# FOOTER
# =========================================================

st.markdown("<br><br>", unsafe_allow_html=True)

st.divider()

st.caption(
    "POLICY INTELLIGENCE  ·  UNDERSTAND THE CONTEXT · RESOLVE THE RULE"
)