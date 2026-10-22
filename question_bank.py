"""
Curated library of ready-made interview Q&A scripts, keyed by role/track, so a
user can try the tool without writing a script from scratch. Meant to be
imported by app.py (e.g. a template picker that drops the chosen text into the
same script_text field a hand-written script would use) — every value here is
valid input to qa_format.parse_qa_text().
"""

TEMPLATES = {
    "Backend Engineer": """\
Q: Tell me about yourself and your background as a backend engineer.
A: I'm a backend engineer with a few years of experience building and maintaining web services, and I enjoy working closely with product teams to ship features end to end. Most of my work has been in Python and Go, building REST and gRPC APIs backed by Postgres and Redis. I care a lot about reliability — writing code that fails predictably and is easy to debug at 2am. Outside of day-to-day feature work, I've also led a couple of migrations, including moving a monolith's billing logic into its own service.

Q: How would you design a URL shortener that needs to handle millions of requests per day?
A: I'd start with a simple schema mapping short codes to long URLs, using a base62 encoding of an auto-incrementing ID or a hash to generate the short code. For read-heavy traffic like this, I'd put a cache like Redis in front of the database so popular redirects don't hit Postgres every time, and I'd use a CDN or edge layer for the redirect itself where possible. On the write side, I'd shard or partition the database once a single instance becomes a bottleneck, and I'd make sure short code generation is collision-safe under concurrent writes. I'd also add rate limiting and basic abuse detection, since URL shorteners are a common target for spam.

Q: Walk me through how you'd debug a production API endpoint that's suddenly returning 500 errors.
A: First I'd check logs and error tracking to see the actual exception and how often it's firing, along with any recent deploys or config changes that line up with when it started. If it correlates with a deploy, I'd consider rolling back immediately to stop the bleeding before digging into the root cause. I'd also check dependencies — database connection pool exhaustion, a downstream service timing out, or a schema migration that didn't match the code are common culprits. Once it's stable, I'd write a quick postmortem and add a test or alert so the same failure mode gets caught earlier next time.

Q: What's the difference between SQL and NoSQL databases, and how do you decide which to use?
A: SQL databases like Postgres give you strong consistency, joins, and transactions, which makes them a good default for data with clear relationships, like users, orders, and payments. NoSQL databases like MongoDB or DynamoDB trade some of that consistency and query flexibility for horizontal scalability and schema flexibility, which suits things like event logs, session data, or rapidly changing document shapes. In practice I default to SQL unless there's a specific reason not to, or a scale requirement a single relational database can't meet. It's also common to use both in the same system for different pieces of data.

Q: How do you approach writing tests for a new feature?
A: I usually start with unit tests for the core business logic, since those are fast and catch the most obvious bugs early. Then I add integration tests for anything that touches the database or external services, often using a test database or mocked clients so the tests stay reliable. For anything user-facing, I'll also think about edge cases — empty inputs, concurrent requests, partial failures — since those are what tend to slip through in manual testing. I try to write tests as I go rather than after the fact, since it's much easier to think about edge cases while I still remember the assumptions I made.""",

    "Frontend Engineer": """\
Q: Tell me about your experience as a frontend engineer.
A: I've spent the last several years building user-facing web applications, mostly with React and TypeScript, for both consumer and internal-tooling products. I'm comfortable owning a feature from design handoff through to shipping, including thinking about accessibility and performance along the way. I particularly enjoy working closely with designers to get the small interaction details right, since that's often what separates a good product from a great one. Recently I've also been doing more work on our component library, trying to cut down on duplicated UI code across teams.

Q: How do you think about performance when building a React application?
A: I start by measuring before optimizing, usually with the browser's performance tools or something like Lighthouse, so I'm fixing real bottlenecks instead of guessing. Common wins are code-splitting routes so users aren't downloading the whole app up front, memoizing expensive computations, and making sure lists with many items are virtualized instead of rendering everything at once. I'm also careful about re-renders — making sure state lives at the right level of the component tree and that props aren't recreated on every render for no reason. Images and fonts are often the biggest contributors to load time, so optimizing those usually gives an outsized improvement for relatively little effort.

Q: What's the difference between controlled and uncontrolled components in React?
A: A controlled component has its value driven entirely by React state, so it always reflects whatever is in state and any change goes through a handler that updates that state. An uncontrolled component manages its own value internally in the DOM, and you read it out when you need it, usually with a ref. Controlled components give you more predictability and make validation or conditional logic easier, which is why they're the default for most forms. Uncontrolled components can be simpler and slightly more performant for things like a single input where you only care about the value on submit.

Q: How would you approach making a web page accessible to users with disabilities?
A: I'd start with semantic HTML — using actual buttons, headings, and form elements instead of styled divs — since that gets you a lot of accessibility for free with screen readers and keyboard navigation. From there I'd make sure every interactive element is reachable and operable by keyboard alone, with visible focus states, and that images and icons have meaningful alt text or are marked decorative. Color contrast matters too, so I'd check that text meets WCAG contrast ratios rather than relying purely on color to convey information. Beyond the technical checklist, I think it helps to actually try navigating the page with a screen reader occasionally, since that surfaces issues an automated audit tool can miss.

Q: Describe a time you had to deal with a particularly tricky CSS layout bug.
A: I once had a flex layout where child elements were overflowing their container only on Safari, while Chrome and Firefox rendered it fine. It turned out Safari was handling min-width differently on flex children, so elements with long unbroken text weren't shrinking the way I expected. I fixed it by explicitly setting min-width to zero on the flex children, which is a well-known Safari flexbox gotcha once you've hit it once. It was a good reminder to actually test layout changes across browsers early, instead of assuming consistent behavior across engines.""",

    "Data Scientist": """\
Q: Tell me about your background in data science.
A: I have a few years of experience working as a data scientist, mostly focused on building predictive models and analytics for product teams. My toolkit is primarily Python — pandas, scikit-learn, and more recently PyTorch for a couple of deep learning projects. I enjoy the full lifecycle of a project, from framing the business question and exploring the data through to deploying a model and monitoring how it performs in production. I also spend a fair amount of time translating results for non-technical stakeholders, since a model is only useful if people trust and act on it.

Q: How do you handle missing or messy data in a dataset?
A: I start by understanding why the data is missing — whether it's missing at random, or whether there's a pattern, like a certain user segment never filling out a particular field. Depending on the amount and type of missingness, I'll either drop the rows or columns, impute with a reasonable default, or use a more sophisticated model-based method if the missingness is significant and non-random. I also think it's important to flag when data was imputed, sometimes with an indicator column, since that itself can be informative for a model. Throughout, I try to avoid silently "fixing" data in a way that introduces bias without documenting what I did and why.

Q: How would you explain the bias-variance tradeoff to a non-technical stakeholder?
A: I'd describe it as a tension between a model being too simple and a model being too complicated. A model with high bias is too simple — it makes strong assumptions and misses real patterns in the data, kind of like trying to fit a straight line to something curved. A model with high variance is too complicated — it fits the training data almost perfectly, including its noise and quirks, but then performs poorly on new data it hasn't seen. The goal is to find a sweet spot in between, which is why we check performance on held-out data rather than just how well a model fits what it was trained on.

Q: Walk me through how you'd evaluate whether a machine learning model is ready to ship.
A: First I'd look at the offline metrics — accuracy, precision and recall, or whatever's appropriate for the problem — on a held-out test set that wasn't used during training or tuning. Beyond the headline number, I'd check performance across important slices of the data, since a model can look good on average while performing badly for a specific segment of users. I'd also want to run an A/B test or shadow deployment before a full rollout, since offline metrics don't always translate directly into the real-world business metric we actually care about. Finally, I'd make sure there's monitoring in place after launch, so we catch model drift or data quality issues before they cause real damage.

Q: Describe a data science project where your initial hypothesis turned out to be wrong.
A: I once assumed that adding more features to a churn prediction model would improve it, since we had access to a lot of additional user behavior data. After adding them, the model's offline metrics barely moved, and a few features were introducing noise that actually hurt performance slightly on certain segments. Digging in, I found that a couple of the new features were leaking information from after the point we were trying to predict churn, which made them look artificially predictive in testing. It was a useful lesson in being more rigorous about feature timing and always double-checking surprisingly good results before trusting them.""",

    "Product Manager": """\
Q: Tell me about your background and how you got into product management.
A: I started out on the engineering side and moved into product management because I enjoyed figuring out what to build even more than building it. Over the past several years I've owned products end to end — talking to users, prioritizing a roadmap, and working closely with design and engineering to ship. I think my engineering background helps me have more grounded conversations with teams about tradeoffs and feasibility. Lately I've been focused on a B2B product, where the stakes of getting requirements right before building are especially high.

Q: How do you prioritize a backlog when everything feels urgent?
A: I try to anchor on a small number of goals for the quarter, so I have a consistent lens to evaluate requests against rather than reacting to whoever asked most recently. For each item I think about impact, effort, and confidence — something high impact but low confidence usually needs more validation before it jumps the queue. I also make a point of separating genuinely urgent issues, like something breaking for customers, from things that just feel urgent because someone's asking loudly. When trade-offs are genuinely close, I'll loop in engineering and design so the prioritization decision isn't made in a vacuum.

Q: Tell me about a time you had to say no to a stakeholder's feature request.
A: A sales lead once pushed hard for a custom integration for one large prospect, and on the surface it looked like an easy win to close the deal. When I dug into the effort estimate with engineering, it would have taken most of a quarter and set a precedent for one-off requests from other large accounts. I showed the stakeholder the roadmap tradeoff explicitly — this feature instead of three other things customers across the board were asking for — and we agreed on a smaller interim solution that unblocked the deal without derailing the roadmap. The key was making the tradeoff visible rather than just saying no outright.

Q: How do you figure out whether a feature actually worked after you ship it?
A: Before shipping, I try to define what success looks like and pick a metric I can actually measure, rather than deciding that after the fact. For most features that means setting up an A/B test or at minimum a clear before-and-after comparison, along with qualitative feedback from users through support tickets or interviews. I give it enough time to reach statistical or practical significance before drawing conclusions, since early data can be noisy and misleading. If a feature doesn't move the needle the way we expected, I try to treat that as useful information rather than a failure, and dig into why.

Q: How do you work with engineering teams when you don't have a technical background in their specific stack?
A: I focus on understanding the problem and constraints well enough to have a real conversation, even if I can't write the code myself — asking what's hard about a request and why, rather than just handing over a spec. I try to involve engineers early, while a feature is still being scoped, so they can flag feasibility issues or suggest a simpler approach before we're committed to a specific design. I also make an effort to learn enough of the domain vocabulary to follow technical discussions, which goes a long way toward building trust with the team. Ultimately I see my job as making sure engineers have clear context on the "why," and trusting them on the "how.\"""",

    "DevOps / SRE": """\
Q: Tell me about your experience with DevOps and site reliability work.
A: I've spent the past few years working on infrastructure and reliability, managing Kubernetes clusters and CI/CD pipelines for a handful of production services. I'm comfortable with the full stack — Terraform for infrastructure as code, Docker and Kubernetes for deployment, and Prometheus and Grafana for monitoring and alerting. A big part of my job has also been on-call, so I care a lot about making systems observable and failures easy to diagnose at 3am. Recently I've been working on reducing our deployment time and improving rollback safety so releases are less risky.

Q: Walk me through how you'd respond to a production outage.
A: First priority is mitigating impact, not finding the root cause — that usually means rolling back a recent deploy, failing over to a healthy region, or scaling up resources if that's the bottleneck. While mitigating, I'd keep stakeholders updated with what's known and what's still being investigated, since silence during an outage is almost worse than the outage itself. Once things are stable, I'd dig into logs, metrics, and traces to understand the actual root cause, rather than settling for the first plausible explanation. Afterward I'd write a blameless postmortem focused on what let the issue happen and what changes would catch it earlier next time.

Q: What's the difference between monitoring and observability?
A: Monitoring is about watching known metrics and alerting when they cross a threshold — things like CPU usage, error rates, or latency that you already know matter. Observability is broader: it's about having enough data, through logs, metrics, and traces, to answer questions you didn't think to ask in advance, especially about novel or unexpected failures. A system can be heavily monitored but not very observable if all you have is dashboards and no way to drill into why a specific request failed. In practice I try to build both — solid alerting on the metrics we know matter, plus enough tracing and structured logging to debug the ones we didn't anticipate.

Q: How do you approach designing a CI/CD pipeline for a new service?
A: I'd start with the basics — automated tests running on every pull request, so broken code can't merge in the first place. For deployment, I'd favor small, frequent releases over big batched ones, since smaller changes are easier to reason about and roll back if something goes wrong. I'd also build in safety mechanisms like canary deployments or feature flags, so a bad change affects a small slice of traffic before it's fully rolled out. Finally, I'd make sure rollback is a one-click, well-tested operation, since the middle of an incident is the worst time to discover that rolling back doesn't actually work.

Q: How do you balance reliability work against feature development when they compete for the same engineering time?
A: I try to frame reliability work in terms of its business impact — downtime cost, customer trust, engineering time lost to firefighting — so it's weighed on the same terms as a new feature rather than dismissed as "just infrastructure." Error budgets are a useful tool here: if a service is burning through its budget, that earns reliability work a real claim on the roadmap rather than it always losing out to features. I also try to find reliability improvements that come nearly free alongside feature work, like adding better observability to a service while it's already being touched. When there's a genuine tradeoff, I'd rather make the cost of the decision visible to leadership than quietly let reliability debt pile up.""",

    "Engineering Manager": """\
Q: Tell me about your path into engineering management.
A: I spent several years as an individual contributor before moving into management, largely because I found I got as much satisfaction from helping other engineers grow as I did from writing code myself. I currently lead a team of engineers working on a core product area, balancing day-to-day delivery with longer-term technical investments. I try to stay close enough to the technical work to have credible conversations and unblock people, without becoming a bottleneck by staying in the code myself. A big part of the job for me is making sure the team has clear priorities and feels supported enough to do their best work.

Q: How do you handle a situation where a team member is consistently underperforming?
A: I'd start with a direct, private conversation to understand what's going on — sometimes it's a skills gap, sometimes it's unclear expectations, and sometimes it's something personal happening outside of work. From there I'd set specific, measurable expectations together and check in regularly, rather than letting weeks go by before the next conversation. I think it's important to document the conversations and give real support, like pairing with a stronger teammate or adjusting workload, before treating it as a performance issue. If things don't improve despite clear expectations and support over a reasonable period, I'd move toward a formal performance plan rather than letting it drag on indefinitely, since that's unfair to both the person and the rest of the team.

Q: How do you decide between making a tough technical decision yourself versus letting the team decide?
A: I lean toward letting the team decide whenever the decision is primarily technical and reversible, since they're closer to the code and will be the ones maintaining it. I'll step in more directly when a decision has significant business tradeoffs, affects multiple teams, or is expensive to reverse later, since those need a wider view than any one engineer typically has. Even when I do make the call, I try to explain my reasoning rather than just announcing a decision, since that builds trust and helps the team calibrate for next time. Mostly my job is making sure the team has the context to make good decisions themselves, so I need to step in as rarely as possible.

Q: How do you approach giving critical feedback to someone on your team?
A: I try to give it as soon as possible after the relevant event, privately, and focus on specific behavior rather than character. I also try to frame it in terms of impact, so the person understands why it matters, not just that I noticed. Wherever I can, I pair the critical feedback with something concrete they can do differently next time, rather than leaving it as a vague impression. I've learned that feedback lands much better when it's a regular habit rather than something that only shows up at a formal review.

Q: How do you keep a distributed or remote team aligned and connected?
A: I over-invest in written communication — clear docs for decisions and context — so people aren't blocked by time zones waiting for a synchronous answer. I also try to protect a few moments of real synchronous connection, like a weekly team call with some non-work time built in, since async alone can make a team feel transactional. For alignment specifically, I make sure goals and priorities are written down somewhere everyone can reference, rather than living only in my head or in one meeting people may have missed. Regular one-on-ones also matter more on a remote team, since I don't get the informal hallway signal that something's off.""",

    "QA / Test Engineer": """\
Q: Tell me about your background in quality assurance and testing.
A: I've worked as a QA and test engineer for several years, moving from manual testing early on into building and maintaining automated test suites. I'm comfortable across the testing pyramid — unit tests, integration tests, and end-to-end tests with tools like Selenium and Playwright. I enjoy the detective-work side of the job, figuring out the edge case nobody thought to check, as much as the automation engineering itself. I also work closely with developers to build quality in from the start, rather than just catching bugs at the end.

Q: How do you decide what to test manually versus what to automate?
A: I automate anything that's repetitive and stable — regression tests for core flows that don't change often — since that's where automation pays off the most over time. Manual testing is better suited to new features that are still changing shape, exploratory testing where you're looking for things you didn't anticipate, and usability issues that are hard to express as a pass or fail assertion. I also weigh the cost of a flaky or brittle automated test against the value it provides; a test that needs constant maintenance can end up costing more time than it saves. In general, I try to automate the boring, repeatable checks so the team's manual testing time goes toward things that actually need human judgment.

Q: Walk me through how you'd write a test plan for a new checkout feature.
A: I'd start by mapping out the main happy path — a user adding an item, entering payment details, and completing the purchase — and make sure that's rock solid first. From there I'd think through edge cases: expired cards, insufficient funds, network failures mid-transaction, applying a discount code, and users abandoning and returning to the cart. I'd also consider cross-cutting concerns like how the feature behaves on mobile versus desktop, and what happens under concurrent load if two requests try to use the same discount code at once. Finally, I'd prioritize which of these get automated regression coverage versus which are checked manually or exploratorily before each release.

Q: How do you handle a bug that you can't reproduce consistently?
A: I start by gathering as much context as possible — exact steps, environment, browser or device, timestamps, and any logs or error messages available, since flaky bugs are often about a specific combination of conditions. I'll try to reproduce it under a few different conditions to see if a pattern emerges, like it only happening under concurrent requests or with a particular data state. If I genuinely can't reproduce it after real effort, I'll add logging or instrumentation around the suspected area so the next occurrence gives us more to go on, rather than closing it as "couldn't reproduce" and hoping it doesn't recur. Intermittent bugs are often the most important ones to chase down, since they tend to point at race conditions that will eventually affect real users.

Q: How do you advocate for quality when there's pressure to ship quickly and skip testing?
A: I try to make the risk visible rather than just saying no — explaining concretely what could break and what the cost of that would be, like a payment bug reaching customers, rather than testing for its own sake. I'll also look for a middle ground, like testing the highest-risk parts thoroughly while accepting lighter coverage on lower-risk parts, so we're not treating all testing as equally non-negotiable. Where possible, I try to build enough automation ahead of time that solid testing doesn't actually cost extra time under pressure. Ultimately I think it's my job to make sure the tradeoff is a conscious decision made by the team, not something that just happens by default because nobody raised it.""",

    "Behavioral / General Fit": """\
Q: Tell me about yourself.
A: I'm someone who's spent the past several years working on software teams, and what's kept me engaged throughout is the combination of solving real problems and working closely with other people to do it. I tend to gravitate toward roles where I can see the impact of my work pretty directly, whether that's a feature users notice or a process change that makes my team faster. Outside of the day-to-day work, I care a lot about continuing to learn — picking up a new skill or going deeper on something I already know. I'm looking for a role where I can keep growing while contributing to something I actually believe in.

Q: Tell me about a time you faced a conflict with a coworker and how you resolved it.
A: I once disagreed pretty strongly with a coworker about the right approach to a project, to the point where it was starting to slow us both down. Instead of letting it fester, I asked to talk it through one-on-one, where I tried to actually understand their reasoning rather than just restating my own position. It turned out we were optimizing for different things — I was focused on speed and they were focused on long-term maintainability — and once that was out in the open, we found a version of the approach that addressed both. The experience taught me that a lot of conflict comes from unstated assumptions, and it's usually worth surfacing those directly instead of just arguing about the conclusion.

Q: Describe a time you failed at something and what you learned from it.
A: Early in a project, I pushed to ship a feature on an aggressive timeline without pushing back on scope, and it ended up going out with several bugs that we had to scramble to fix afterward. Looking back, I hadn't been honest enough with myself or my team about the risk, mostly because I didn't want to be the person asking for more time. Since then, I've gotten much more comfortable flagging risk early and proposing a smaller, more reliable scope rather than a bigger one I'm not confident about. It was a useful, if uncomfortable, lesson in valuing honesty about risk over looking agreeable in the short term.

Q: Tell me about a time you had to learn something completely new in a short amount of time.
A: On a previous project, I was asked to take ownership of a part of the system built on a technology I'd never used before, with a deadline just a few weeks out. I spent the first couple of days deliberately going broad — reading documentation and skimming the existing codebase — before diving into the actual task, which saved me from going down wrong paths later. I also leaned heavily on a colleague who knew the technology well, asking targeted questions instead of trying to figure everything out alone. I ended up delivering the feature on time, and it gave me a lot of confidence that I can get productive in an unfamiliar area quickly when I need to.

Q: Why do you want to work here, and where do you see yourself in a few years?
A: I'm drawn to this role because it sits right at the intersection of things I'm good at and things I actually want to get better at, and from what I've learned about the team, the problems you're working on seem both hard and genuinely useful. In a few years, I'd like to have grown significantly in scope — taking on bigger or more ambiguous problems — while also having built a reputation as someone people want to work with. I'm less attached to a specific title and more to making sure I'm learning and that my work is actually mattering to the people who use it. This role looks like a strong place to do that, which is why I'm excited about it.""",
}


def list_templates():
    return sorted(TEMPLATES)


def get_template(name):
    try:
        return TEMPLATES[name]
    except KeyError:
        raise ValueError(
            f"No question bank template named {name!r}. "
            f"Available templates: {', '.join(list_templates())}"
        )


if __name__ == "__main__":
    for name in list_templates():
        print(name)
