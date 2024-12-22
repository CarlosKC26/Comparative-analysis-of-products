import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow import keras
from sklearn.model_selection import StratifiedKFold
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, confusion_matrix
from pandas.api.types import CategoricalDtype
import joblib

# Cargar datos
df = pd.read_excel("src\\comparative_analysis\\models\\RedNeuronal\\productos_con_clusters.xlsx")

# Ajustar nombres de columnas según disponibilidad real en el DataFrame.
# Ejemplo si la columna se llama "Drop heel-to-toe differential":
numerical_cols = ['Drop__heel-to-toe_differential_', 'Weight', 'regularPrice','undiscounted_price','percentil_discounted']
categorical_cols = ['Midsole_Material', 'Cushioning_System', 'Outsole', 'Upper_Material', 
                    'Additional_Technologies', 'Gender']

target_col = 'Cluster'
df = df.dropna(subset=[target_col])

X = df[numerical_cols + categorical_cols]
y = df[target_col]

# Convertir a categoría si no lo es ya
if not isinstance(y.dtype, CategoricalDtype):
    y = y.astype('category')

num_classes = len(y.cat.categories)

numeric_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='median')),
    ('scaler', StandardScaler())
])

categorical_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='most_frequent')),
    # Para versiones de scikit-learn >= 1.2, usar 'sparse_output=False'
    # Si tienes una versión más antigua, usa 'sparse=False' si está disponible o retira el argumento
    ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
])

preprocessor = ColumnTransformer(
    transformers=[
        ('num', numeric_transformer, numerical_cols),
        ('cat', categorical_transformer, categorical_cols)
    ]
)

skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

all_reports = []
all_conf_matrices = []

for fold, (train_index, test_index) in enumerate(skf.split(X, y)):
    X_train, X_val = X.iloc[train_index], X.iloc[test_index]
    y_train, y_val = y.iloc[train_index], y.iloc[test_index]


    X_train_processed = preprocessor.fit_transform(X_train)
    X_val_processed = preprocessor.transform(X_val)
    
    y_train_cat = keras.utils.to_categorical(y_train.cat.codes, num_classes=num_classes)
    y_val_cat = keras.utils.to_categorical(y_val.cat.codes, num_classes=num_classes)

    model = keras.Sequential([
        keras.layers.Input(shape=(X_train_processed.shape[1],)),
        keras.layers.Dense(64, activation='relu', kernel_regularizer=keras.regularizers.l2(0.001)),
        keras.layers.Dropout(0.3),
        keras.layers.Dense(32, activation='relu', kernel_regularizer=keras.regularizers.l2(0.001)),
        keras.layers.Dropout(0.3),
        keras.layers.Dense(num_classes, activation='softmax')
    ])

    
    model.compile(loss='categorical_crossentropy', optimizer='adam', metrics=['accuracy'])
    
    early_stopping = keras.callbacks.EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)
    
    history = model.fit(
        X_train_processed, y_train_cat,
        validation_data=(X_val_processed, y_val_cat),
        epochs=100,
        batch_size=16,
        callbacks=[early_stopping],
        verbose=0
    )
    
    val_loss, val_acc = model.evaluate(X_val_processed, y_val_cat, verbose=0)
    
    y_pred_proba = model.predict(X_val_processed)
    y_pred = np.argmax(y_pred_proba, axis=1)
    y_true = y_val.cat.codes


    report = classification_report(y_true, y_pred)
    conf_mat = confusion_matrix(y_true, y_pred)
    
    all_reports.append(report)
    all_conf_matrices.append(conf_mat)


model.save("src\comparative_analysis\models\RedNeuronal\modelo_entrenado.keras")
# Guardar el preprocessor
joblib.dump(preprocessor, "src/comparative_analysis/models/RedNeuronal/preprocessor.pkl")