df = pd.read_csv('crop_recommendation.csv')

X = df.drop('label', axis=1)
y = df['label']

X_train, X_test, y_train, y_test = train_test_split(...)
model = RandomForestClassifier(...)
model.fit(X_train, y_train)

joblib.dump(model, "farmer_advisory_model.pkl")

CROP_RANGES = df.groupby('label').agg(['min','max']).to_dict()
joblib.dump(CROP_RANGES, "crop_ranges.pkl")